"""
供水系统韧性分析仿真主程序
"""

import wntr
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
import os


# ============================================================================
# 数据库类
# ============================================================================
class SimulationDB:
    def __init__(self, db_path='scada_sim.db'):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
            timestamp REAL, sensor_id TEXT, value REAL, unit TEXT,
            is_fault INTEGER DEFAULT 0, true_value REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS actuator_status (
            timestamp REAL, actuator_id TEXT, status INTEGER, source TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS pump_physical_status (
            timestamp REAL, pump_id TEXT, status INTEGER,
            is_fault_overridden INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS control_log (
            timestamp REAL, action TEXT, reason TEXT,
            is_under_fault INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS fault_log (
            timestamp REAL, fault_type TEXT,
            affected_pumps TEXT, description TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS early_warning_log (
            timestamp REAL, warning_level TEXT,
            trigger_tank TEXT, tank_level REAL,
            pump_physical_status INTEGER,
            trigger_threshold REAL,
            demand_reduction REAL,
            action TEXT, description TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS performance_data (
            timestamp    REAL,
            RI           REAL,
            avg_pressure REAL)''')
        self.conn.commit()

    def write_sensor(self, timestamp, sensor_id, value, unit='',
                     is_fault=0, true_value=None):
        if true_value is None:
            true_value = value
        self.conn.execute('INSERT INTO sensor_data VALUES (?,?,?,?,?,?)',
                          (float(timestamp), sensor_id, float(value), unit,
                           int(is_fault), float(true_value)))
        self.conn.commit()

    def write_actuator(self, timestamp, actuator_id, status, source='PLC'):
        self.conn.execute('INSERT INTO actuator_status VALUES (?,?,?,?)',
                          (timestamp, actuator_id, status, source))
        self.conn.commit()

    def write_pump_physical_status(self, timestamp, pump_id, status, is_fault_overridden):
        self.conn.execute('INSERT INTO pump_physical_status VALUES (?,?,?,?)',
                          (timestamp, pump_id, status, is_fault_overridden))
        self.conn.commit()

    def write_fault_log(self, timestamp, fault_type, affected_pumps, description):
        self.conn.execute('INSERT INTO fault_log VALUES (?,?,?,?)',
                          (timestamp, fault_type, ','.join(affected_pumps), description))
        self.conn.commit()

    def write_early_warning_log(self, timestamp, warning_level, trigger_tank, tank_level,
                                pump_physical_status, trigger_threshold,
                                demand_reduction, action, description):
        self.conn.execute('INSERT INTO early_warning_log VALUES (?,?,?,?,?,?,?,?,?)',
                          (timestamp, warning_level, trigger_tank, tank_level,
                           pump_physical_status, trigger_threshold,
                           demand_reduction, action, description))
        self.conn.commit()

    def write_performance(self, timestamp, RI, avg_pressure=None):
        self.conn.execute('INSERT INTO performance_data VALUES (?,?,?)',
                          (timestamp, RI, avg_pressure))
        self.conn.commit()

    def write_log(self, timestamp, action, reason, is_under_fault=0):
        self.conn.execute('INSERT INTO control_log VALUES (?,?,?,?)',
                          (timestamp, action, reason, is_under_fault))
        self.conn.commit()

    def get_latest_actuator(self, actuator_id):
        c = self.conn.execute('SELECT status FROM actuator_status '
                              'WHERE actuator_id=? ORDER BY timestamp DESC LIMIT 1', (actuator_id,))
        r = c.fetchone()
        return r[0] if r else None

    def get_latest_pump_physical_status(self, pump_id):
        c = self.conn.execute('SELECT status FROM pump_physical_status '
                              'WHERE pump_id=? ORDER BY timestamp DESC LIMIT 1', (pump_id,))
        r = c.fetchone()
        return r[0] if r else None

    def get_latest_sensor_with_fault_flag(self, sensor_id):
        c = self.conn.execute('SELECT value, is_fault, true_value FROM sensor_data '
                              'WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1', (sensor_id,))
        r = c.fetchone()
        return {'value': r[0], 'is_fault': r[1], 'true_value': r[2]} if r else None

    def close(self):
        self.conn.close()


# ============================================================================
# 水源中断故障场景
# ============================================================================
class WaterSourceInterruption:
    def __init__(self, fault_start_time=24*3600, fault_duration=24*3600, affected_pumps=None):
        self.fault_start_time = fault_start_time
        self.fault_duration = fault_duration
        self.fault_end_time = fault_start_time + fault_duration
        self.affected_pumps = affected_pumps
        self.is_active = False
        self.fault_logged = False

    def is_fault_active(self, current_time):
        return self.fault_start_time <= current_time < self.fault_end_time

    def apply_fault(self, current_time, pump_name, intended_status):
        if not self.is_fault_active(current_time):
            self.is_active = False
            return intended_status, False
        if self.affected_pumps is None or pump_name in self.affected_pumps:
            self.is_active = True
            return 0, True
        return intended_status, False


# ============================================================================
# 早期预警系统（三级阶梯 + 双重时间门控）
# ============================================================================
class EarlyWarningSystem:
    LEVELS = [
        ('CRITICAL', 2.0, 0.20, 3),
        ('ALERT',    4.0, 0.40, 2),
        ('WARNING',  5.0, 0.70, 1),
    ]
    LEVEL_RANK = {'NORMAL': 0, 'WARNING': 1, 'ALERT': 2, 'CRITICAL': 3}
    REDUCTION_MAP = {lv: rd for lv, _, rd, _ in LEVELS}
    REDUCTION_MAP['NORMAL'] = 1.0
    THRESHOLD_MAP = {lv: thr for lv, thr, _, _ in LEVELS}

    def __init__(self, db, tank_pump_map, fault_start_time, fault_end_time):
        self.db = db
        self.tank_pump_map = tank_pump_map
        self.fault_start_time = fault_start_time
        self.fault_end_time = fault_end_time
        self.current_level = 'NORMAL'
        self.current_reduction = 1.0
        self.warning_triggered = False
        self.warning_first_time = None
        self.level_history = []

    def _evaluate_tank(self, level, pump_physical_status):
        if pump_physical_status != 0:
            return 'NORMAL', None
        for lv_name, threshold, _, _ in self.LEVELS:
            if level < threshold:
                return lv_name, threshold
        return 'NORMAL', None

    def evaluate(self, current_time, tank_levels):
        if current_time < self.fault_start_time:
            return 1.0, 'NORMAL'

        if current_time >= self.fault_end_time:
            if self.current_level != 'NORMAL':
                prev = self.current_level
                self.current_level = 'NORMAL'
                self.current_reduction = 1.0
                self.db.write_early_warning_log(
                    current_time, 'NORMAL', '-', 0.0, 1, 0.0, 1.0,
                    '故障结束：解除预警，需求恢复正常',
                    f'故障于 {self.fault_end_time/3600:.1f}h 结束，{prev} -> NORMAL')
                self.db.write_log(current_time, '故障结束：需求恢复100%',
                                  f'{prev} -> NORMAL', is_under_fault=0)
            return 1.0, 'NORMAL'

        prev_level = self.current_level
        worst_level = 'NORMAL'
        worst_thr = None
        worst_tank = None
        worst_lv = None
        worst_ps = None

        for tank_id, level in tank_levels.items():
            pump_id = self.tank_pump_map.get(tank_id)
            if pump_id is None:
                continue
            phys = self.db.get_latest_pump_physical_status(pump_id)
            if phys is None:
                phys = 1
            lv, thr = self._evaluate_tank(level, phys)
            if self.LEVEL_RANK[lv] > self.LEVEL_RANK[worst_level]:
                worst_level = lv
                worst_thr = thr
                worst_tank = tank_id
                worst_lv = level
                worst_ps = phys

        if self.LEVEL_RANK[worst_level] < self.LEVEL_RANK[self.current_level]:
            worst_level = self.current_level

        self.current_level = worst_level
        self.current_reduction = self.REDUCTION_MAP[worst_level]

        if (self.LEVEL_RANK[worst_level] >= self.LEVEL_RANK['WARNING']
                and not self.warning_triggered):
            self.warning_triggered = True
            self.warning_first_time = current_time

        if worst_level != prev_level:
            rd = self.REDUCTION_MAP[worst_level]
            desc = (f"水箱 {worst_tank} 水位={worst_lv:.3f}m < {worst_thr}m，"
                    f"水泵物理关闭；需求削减至 {rd*100:.0f}%")
            self.db.write_early_warning_log(
                current_time, worst_level, worst_tank or '-', worst_lv or 0.0,
                worst_ps or 0, worst_thr or 0.0, rd,
                f"{prev_level} -> {worst_level}：需求×{rd:.2f}", desc)
            self.db.write_log(current_time, f"EWS: {prev_level}->{worst_level} 需求×{rd:.2f}",
                              desc, is_under_fault=1)
            self.level_history.append({'time_h': current_time/3600,
                                       'level': worst_level, 'reduction': rd})

        return self.current_reduction, self.current_level


# ============================================================================
# PLC 控制器
# ============================================================================
class PLC:
    def __init__(self, db):
        self.db = db
        self.rules = {'T1': {'pump': 'P1', 'low': 5.0, 'high': 8.0},
                      'T2': {'pump': 'P2', 'low': 5.0, 'high': 8.0}}
        self.pump_states = {}

    def control(self, current_time):
        for tank, rule in self.rules.items():
            data = self.db.get_latest_sensor_with_fault_flag(tank)
            if data is None:
                continue
            level = data['value']
            pump = rule['pump']
            current = self.pump_states.get(pump, self.db.get_latest_actuator(pump))
            if current is None:
                current = 1
            if current == 0 and level < rule['low']:
                new = 1
            elif current == 1 and level > rule['high']:
                new = 0
            else:
                new = current
            if new != current:
                self.db.write_actuator(current_time, pump, new, 'PLC')
            self.pump_states[pump] = new


# ============================================================================
# 步进仿真引擎（基类）
# ============================================================================
class SteppedSim:
    MIN_WATER_LEVEL = 0.05
    OUTLET_HEIGHT = 0.50

    def __init__(self, inp_file, db_path='scada_sim.db', timestep=300,
                 fault_scenario=None, demand_factor=1.5, verbose=False):
        self.verbose = verbose
        self.inp_file = inp_file
        self.wn = wntr.network.WaterNetworkModel(inp_file)
        self.db = SimulationDB(db_path)
        self.timestep = timestep
        self.current_time = 0
        self.step = 0
        self.base_demand_factor = demand_factor
        self.current_demand_factor = demand_factor
        self.fault_scenario = fault_scenario
        self.outlet_failed = {}
        self.outlet_failure_time = {}
        self.previous_levels = {}
        self.P0 = None
        self.P0_recorded = False
        self._last_pre_fault_avg = None
        self.fault_start_time = (fault_scenario.fault_start_time if fault_scenario else 24*3600)
        self.fault_end_time = (fault_scenario.fault_end_time if fault_scenario else 48*3600)

        for ctrl in list(self.wn.control_name_list):
            self.wn.remove_control(ctrl)
        for tank_name in self.wn.tank_name_list:
            self.wn.get_node(tank_name).min_level = self.MIN_WATER_LEVEL
            self.outlet_failed[tank_name] = False

        self._apply_pattern(demand_factor)

        self.tanks = self.wn.tank_name_list
        self.pumps = self.wn.pump_name_list
        self.all_junctions = self.wn.junction_name_list

        self.tank_levels = {}
        for tank in self.tanks:
            lvl = self.wn.get_node(tank).init_level
            self.tank_levels[tank] = lvl
            self.previous_levels[tank] = lvl

        self._identify_tank_outlets()

    def _identify_tank_outlets(self):
        self.tank_outlet_pipes = {}
        for t in self.tanks:
            self.tank_outlet_pipes[t] = [p for p in self.wn.pipe_name_list
                                         if self.wn.get_link(p).start_node_name == t]

    def _apply_pattern(self, demand_factor):
        original = [0.046, 0.031, 0.038, 0.025, 0.046, 0.072,
                    0.076, 0.110, 0.111, 0.083, 0.066, 0.074,
                    0.066, 0.060, 0.073, 0.063, 0.064, 0.080,
                    0.071, 0.073, 0.059, 0.050, 0.062, 0.063]
        enhanced = [x * demand_factor for x in original]
        pname = 'SIM_PATTERN'
        if pname in self.wn.pattern_name_list:
            self.wn.remove_pattern(pname)
        self.wn.add_pattern(pname, enhanced)
        for junc in self.wn.junction_name_list:
            for d in self.wn.get_node(junc).demand_timeseries_list:
                if d.base_value > 0:
                    d.base_value *= demand_factor
                    d.pattern_name = pname

    def _update_demand_factor(self, new_factor):
        if abs(new_factor - self.current_demand_factor) < 1e-6:
            return
        ratio = new_factor / self.current_demand_factor
        for junc in self.wn.junction_name_list:
            for d in self.wn.get_node(junc).demand_timeseries_list:
                if d.base_value > 0:
                    d.base_value *= ratio
        self.current_demand_factor = new_factor

    def apply_pump_control(self):
        for ctrl in list(self.wn.control_name_list):
            self.wn.remove_control(ctrl)
        for pump_name in self.pumps:
            plc_status = self.db.get_latest_actuator(pump_name)
            if plc_status is None:
                plc_status = 1
            if self.fault_scenario:
                actual, overridden = self.fault_scenario.apply_fault(
                    self.current_time, pump_name, plc_status)
                if overridden and not self.fault_scenario.fault_logged:
                    self.db.write_fault_log(self.current_time, 'WATER_SOURCE_INTERRUPTION',
                                            list(self.pumps), '水源中断：水泵无法向水箱供水')
                    self.fault_scenario.fault_logged = True
            else:
                actual, overridden = plc_status, False
            self.db.write_pump_physical_status(self.current_time, pump_name, actual, int(overridden))
            pump = self.wn.get_link(pump_name)
            status = (wntr.network.LinkStatus.Open if actual == 1
                      else wntr.network.LinkStatus.Closed)
            act = wntr.network.controls.ControlAction(pump, 'status', status)
            cond = wntr.network.controls.SimTimeCondition(self.wn, '=', 0)
            self.wn.add_control(f'SIM_{pump_name}',
                                wntr.network.controls.Control(cond, act))

    def control_tank_outlets(self):
        for tank_name in self.tanks:
            level = self.tank_levels[tank_name]
            for pipe_name in self.tank_outlet_pipes.get(tank_name, []):
                pipe = self.wn.get_link(pipe_name)
                if level < self.OUTLET_HEIGHT:
                    pipe.initial_status = wntr.network.LinkStatus.Closed
                    if not self.outlet_failed[tank_name]:
                        self.outlet_failed[tank_name] = True
                        self.outlet_failure_time[tank_name] = self.current_time
                else:
                    pipe.initial_status = wntr.network.LinkStatus.Open
                    self.outlet_failed[tank_name] = False

    def _calc_raw_avg_pressure(self, results, sim_time):
        total = 0.0
        count = len(self.all_junctions)
        for junction in self.all_junctions:
            head = results.node['head'].loc[sim_time, junction]
            elev = self.wn.get_node(junction).elevation
            total += max(0.0, head - elev)
        return total / count if count > 0 else 0.0

    def calculate_system_state(self, results, sim_time):
        raw_avg = self._calc_raw_avg_pressure(results, sim_time)
        if self.current_time < self.fault_start_time:
            self._last_pre_fault_avg = raw_avg
            RI = 1.0
        elif self.current_time == self.fault_start_time:
            if not self.P0_recorded:
                self.P0 = (self._last_pre_fault_avg
                           if self._last_pre_fault_avg is not None else raw_avg)
                self.P0_recorded = True
            RI = raw_avg / self.P0 if self.P0 > 0 else 0.0
        elif self.fault_start_time < self.current_time <= self.fault_end_time:
            RI = raw_avg / self.P0 if (self.P0 and self.P0 > 0) else 0.0
        else:
            RI = 1.0
        RI = float(np.clip(RI, 0.0, 1.0))
        self.db.write_performance(self.current_time, RI, raw_avg)
        return RI, raw_avg

    def write_sensors(self, results, sim_time):
        is_fault = (self.fault_scenario.is_active if self.fault_scenario else False)
        for tank in self.tanks:
            head = results.node['head'].loc[sim_time, tank]
            elev = self.wn.get_node(tank).elevation
            level = max(self.MIN_WATER_LEVEL, head - elev)
            self.previous_levels[tank] = level
            self.db.write_sensor(self.current_time, tank, level, 'm',
                                 is_fault=int(is_fault), true_value=level)
        for pump in self.pumps:
            flow = results.link['flowrate'].loc[sim_time, pump] * 3600
            self.db.write_sensor(self.current_time, f"{pump}_flow", flow, 'm3/h')

    def record_initial_state(self):
        for tank in self.tanks:
            self.db.write_sensor(0, tank, self.tank_levels[tank], 'm')
        for pump in self.pumps:
            self.db.write_pump_physical_status(0, pump, 1, 0)
        self.wn.options.time.duration = self.timestep
        self.wn.options.time.hydraulic_timestep = self.timestep
        self.wn.options.time.report_timestep = self.timestep
        results = wntr.sim.EpanetSimulator(self.wn).run_sim()
        initial_time = results.node['head'].index[0]
        raw_avg = self._calc_raw_avg_pressure(results, initial_time)
        self._last_pre_fault_avg = raw_avg
        self.db.write_performance(0, 1.0, raw_avg)

    def run_step(self, ew_demand_reduction=1.0):
        self._update_demand_factor(self.base_demand_factor * ew_demand_reduction)
        for tank in self.tanks:
            self.wn.get_node(tank).init_level = max(self.MIN_WATER_LEVEL, self.tank_levels[tank])
        self.control_tank_outlets()
        self.apply_pump_control()
        self.wn.options.time.duration = self.timestep
        self.wn.options.time.hydraulic_timestep = self.timestep
        self.wn.options.time.report_timestep = self.timestep
        results = wntr.sim.EpanetSimulator(self.wn).run_sim()
        for tank in self.tanks:
            head = results.node['head'].loc[self.timestep, tank]
            elev = self.wn.get_node(tank).elevation
            self.tank_levels[tank] = max(self.MIN_WATER_LEVEL, head - elev)
        self.current_time += self.timestep
        self.write_sensors(results, self.timestep)
        self.calculate_system_state(results, self.timestep)
        self.step += 1
        return results

    def close(self):
        self.db.close()


class NoEWSim(SteppedSim):
    def __init__(self, inp_file, db_path='scada_sim.db', timestep=300,
                 fault_scenario=None, demand_factor=1.5, verbose=False):
        super().__init__(inp_file, db_path, timestep, fault_scenario, demand_factor, verbose)
        self.plc = PLC(self.db)
        for pump in self.pumps:
            self.db.write_actuator(0, pump, 1, 'INIT')

    def run(self, duration):
        steps = int(duration / self.timestep)
        self.record_initial_state()
        for i in range(steps):
            if i > 0:
                self.plc.control(self.current_time)
            self.run_step(ew_demand_reduction=1.0)


class EWSim(SteppedSim):
    def __init__(self, inp_file, db_path='scada_sim.db', timestep=300,
                 fault_scenario=None, demand_factor=1.5, verbose=False):
        super().__init__(inp_file, db_path, timestep, fault_scenario, demand_factor, verbose)
        self.plc = PLC(self.db)
        for pump in self.pumps:
            self.db.write_actuator(0, pump, 1, 'INIT')
        tank_pump_map = {tank: f"P{tank[-1]}" for tank in self.tanks}
        self.ews = EarlyWarningSystem(db=self.db, tank_pump_map=tank_pump_map,
                                      fault_start_time=self.fault_start_time,
                                      fault_end_time=self.fault_end_time)

    def run(self, duration):
        steps = int(duration / self.timestep)
        self.record_initial_state()
        for i in range(steps):
            if i > 0:
                self.plc.control(self.current_time)
            reduction, _ = self.ews.evaluate(self.current_time, self.tank_levels)
            self.run_step(ew_demand_reduction=reduction)


# ============================================================================
# 韧性分析器（精简：只保留计算，绘图从略以便快速复现）
# ============================================================================
def calc_RI(db_path, td, tr):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f"SELECT timestamp, RI FROM performance_data "
                     f"WHERE timestamp >= {td} AND timestamp <= {tr} ORDER BY timestamp", conn)
    conn.close()
    if df.empty or len(df) < 2:
        return None
    ts = df['timestamp'].values
    ri_vals = df['RI'].values
    duration = tr - td
    area = np.trapz(ri_vals, ts)
    return float(np.clip(area/duration, 0.0, 1.0)) if duration > 0 else None


def state_durations(db_path, tank_id, td, tr, timestep=300):
    """按论文风险阈值统计各状态时长(h) —— 用于复现 Fig4(b)/Table2"""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f"SELECT timestamp, value FROM sensor_data "
                     f"WHERE sensor_id='{tank_id}' AND timestamp>={td} AND timestamp<={tr} "
                     f"ORDER BY timestamp", conn)
    conn.close()
    def classify(h):
        if h >= 5.0: return 'Normal'
        if h >= 4.0: return 'Warning'
        if h >= 2.0: return 'Alert'
        if h >= 0.5: return 'Critical'
        return 'OutletFailure'
    dur = {}
    for _, row in df.iterrows():
        s = classify(row['value'])
        dur[s] = dur.get(s, 0) + timestep/3600.0
    return dur


def run_one(mode, inp_file, base='resilience_water_source',
            duration=3*24*3600, timestep=300, demand_factor=1.5,
            fault_start=24*3600, fault_duration=24*3600):
    os.makedirs(base, exist_ok=True)
    db_path = os.path.join(base, f'{mode}.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    fault = WaterSourceInterruption(fault_start, fault_duration, affected_pumps=None)
    SimClass = NoEWSim if mode == 'no_ew' else EWSim
    sim = SimClass(inp_file, db_path, timestep, fault_scenario=fault,
                   demand_factor=demand_factor, verbose=False)
    sim.run(duration)
    P0 = sim.P0
    ews_hist = sim.ews.level_history if mode == 'ew' else []
    sim.close()
    fault_end = fault_start + fault_duration
    RI = calc_RI(db_path, fault_start, fault_end)
    return {'mode': mode, 'P0': P0, 'RI': RI, 'db_path': db_path,
            'fault_start': fault_start, 'fault_end': fault_end, 'ews_hist': ews_hist}


if __name__ == "__main__":
    INP = 'anytown.inp'
    print("Reproducing ORIGINAL results (pressure-only RI)...")
    rn = run_one('no_ew', INP)
    re = run_one('ew', INP)
    print(f"\n{'='*50}")
    print(f"  No EW  : P0={rn['P0']:.4f} m   RI={rn['RI']:.4f}")
    print(f"  With EW: P0={re['P0']:.4f} m   RI={re['RI']:.4f}")
    print(f"  Delta RI = {re['RI']-rn['RI']:+.4f}")
    print(f"{'='*50}")
    for mode, r in [('NoEW', rn), ('EW', re)]:
        for t in ['T1', 'T2']:
            d = state_durations(r['db_path'], t, r['fault_start'], r['fault_end'])
            print(f"  [{mode}] {t} durations(h): " +
                  ", ".join(f"{k}={v:.2f}" for k, v in d.items()))
    print("  EW level history:", re['ews_hist'])

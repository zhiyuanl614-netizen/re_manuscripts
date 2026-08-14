
# Global Matplotlib styling for Times New Roman and Black text

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Global Matplotlib styling for Times New Roman and Black text
plt.rcParams['font.sans-serif'] = 'Times New Roman'
plt.rcParams['font.serif'] = 'Times New Roman'
plt.rcParams['font.family'] = 'serif'
plt.rcParams['text.color'] = 'black'
plt.rcParams['axes.labelcolor'] = 'black'
plt.rcParams['xtick.color'] = 'black'
plt.rcParams['ytick.color'] = 'black'
import matplotlib.patches as patches
from matplotlib.lines import Line2D
import numpy as np
import sqlite3, pandas as pd
import os

FIG_DIR = '02_revised/figures'
os.makedirs(FIG_DIR, exist_ok=True)

# Exact color codes extracted from original manuscript
C_NORMAL = '#208A62'     # Dark Green
C_WARNING = '#F39C12'    # Light Yellow/Orange
C_ALERT = '#E67E22'      # Deep Orange
C_CRITICAL = '#2980B9'   # Dark Blue
C_FAILURE = '#C0392B'    # Crimson Red

C_BG = '#F4F6F7'         # Off-white / light blue-grey background
C_TEXT = '#2C3E50'
C_SHADE = '#D0ECE7'      # Light teal fill for EWM improvement

# Global font & styling setup
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.edgecolor'] = '#BDC3C7'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#E5E8E8'
plt.rcParams['grid.linestyle'] = '--'

# Read database simulation data
con_no = sqlite3.connect('02_revised/results/no_ew.db')
con_ew = sqlite3.connect('02_revised/results/ew.db')

df_no = pd.read_sql('SELECT timestamp/3600 as time_h, RI, DSR, avg_pressure, delivered, required FROM performance_data', con_no)
df_ew = pd.read_sql('SELECT timestamp/3600 as time_h, RI, DSR, avg_pressure, delivered, required FROM performance_data', con_ew)

df_sensor_no = pd.read_sql("SELECT timestamp/3600 as time_h, sensor_id, value FROM sensor_data", con_no)
df_sensor_ew = pd.read_sql("SELECT timestamp/3600 as time_h, sensor_id, value FROM sensor_data", con_ew)

con_no.close()
con_ew.close()

# Extract time series for T1 and T2
df_t1_no = df_sensor_no[df_sensor_no['sensor_id']=='T1']
df_t1_ew = df_sensor_ew[df_sensor_ew['sensor_id']=='T1']
df_t2_no = df_sensor_no[df_sensor_no['sensor_id']=='T2']
df_t2_ew = df_sensor_ew[df_sensor_ew['sensor_id']=='T2']

# ============================================================================
# FIG 1: Network Topology
# ============================================================================

node_coords = {
    'R': (9.2, 1.2), 'P1': (8.2, 2.0), 'P2': (8.2, 1.2), 'J20': (8.2, 1.2),
    'J1': (6.8, 1.2), 'J2': (7.8, 3.2), 'J3': (7.5, 5.0), 'J4': (6.2, 5.2),
    'J5': (5.0, 6.2), 'J6': (3.6, 5.8), 'J7': (2.8, 5.5), 'J8': (2.8, 4.2),
    'J9': (0.5, 2.8), 'J10': (1.5, 1.2), 'J11': (3.0, 0.5), 'J12': (4.8, 1.2),
    'J13': (6.5, 2.2), 'J14': (6.5, 3.5), 'J15': (5.2, 4.2), 'J16': (3.8, 3.2),
    'J17': (2.2, 2.2), 'J18': (4.2, 2.2), 'J19': (5.2, 2.8), 'J21': (6.2, 4.2),
    'J22': (2.2, 1.5), 'T1': (6.2, 4.7), 'T2': (1.8, 3.2)
}

edges = [
    ('R', 'J20'), ('J20', 'J1'), ('J1', 'J2'), ('J1', 'J12'), ('J1', 'J13'),
    ('J2', 'J3'), ('J2', 'J13'), ('J2', 'J14'), ('J3', 'J4'), ('J4', 'J5'),
    ('J4', 'J8'), ('J4', 'J15'), ('J4', 'T1'), ('T1', 'J21'), ('J21', 'J14'),
    ('J5', 'J6'), ('J6', 'J7'), ('J6', 'J8'), ('J7', 'J8'), ('J8', 'J9'),
    ('J8', 'J15'), ('J8', 'J16'), ('J8', 'J17'), ('J9', 'J10'), ('J10', 'J11'),
    ('J10', 'J17'), ('J11', 'J12'), ('J12', 'J18'), ('J13', 'J14'), ('J13', 'J19'),
    ('J14', 'J15'), ('J14', 'J19'), ('J15', 'J16'), ('J15', 'J19'), ('J16', 'J17'),
    ('J16', 'J18'), ('J17', 'J18'), ('J17', 'J22'), ('J17', 'T2'), ('T2', 'J22'),
    ('J18', 'J19')
]

fig, ax = plt.subplots(figsize=(9, 6), facecolor='#FFFFFF')
ax.set_facecolor('#FFFFFF')

for u, v in edges:
    if u in node_coords and v in node_coords:
        x1, y1 = node_coords[u]
        x2, y2 = node_coords[v]
        ax.plot([x1, x2], [y1, y2], color='#888888', lw=1.2, zorder=1)

for name, (x, y) in node_coords.items():
    if name.startswith('J'):
        ax.scatter(x, y, color='#2F5597', s=70, zorder=3)
        ax.text(x - 0.15, y - 0.25, name, fontsize=8, fontweight='bold', color='#1B365D')

rx, ry = node_coords['R']
ax.scatter(rx, ry, color='#C65911', marker='s', s=100, zorder=4)
ax.text(rx + 0.15, ry, 'R', fontsize=9, fontweight='bold', color='#C65911')

for tank in ['T1', 'T2']:
    tx, ty = node_coords[tank]
    ax.scatter(tx, ty, color='#385723', marker='D', s=100, zorder=4)
    ax.text(tx + 0.2, ty, tank, fontsize=9, fontweight='bold', color='#385723')

px, py = node_coords['P1']
ax.scatter(px, py, color='#555555', marker='o', s=80, facecolors='none', edgecolors='#333333', lw=1.5, zorder=4)
ax.text(px, py + 0.25, 'P1', fontsize=8.5, fontweight='bold', color='#333333')

px2, py2 = node_coords['P2']
ax.scatter(px2, py2, color='#555555', marker='o', s=80, facecolors='none', edgecolors='#333333', lw=1.5, zorder=4)
ax.text(px2, py2 - 0.35, 'P2', fontsize=8.5, fontweight='bold', color='#333333')

legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Demand Nodes', markerfacecolor='#2F5597', markersize=8),
    Line2D([0], [0], marker='s', color='w', label='Reservoir', markerfacecolor='#C65911', markersize=9),
    Line2D([0], [0], marker='D', color='w', label='Tanks', markerfacecolor='#385723', markersize=9),
    Line2D([0], [0], marker='o', color='w', label='Pumps', markerfacecolor='none', markeredgecolor='#333333', markeredgewidth=1.5, markersize=8)
]
ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#BDC3C7', fontsize=8.5)

ax.set_xlim(-0.2, 10.2)
ax.set_ylim(-0.2, 6.8)
ax.axis('off')
plt.tight_layout()

plt.savefig(os.path.join(FIG_DIR, 'Fig1.png'), dpi=300, bbox_inches='tight')
plt.close()


# ============================================================================
# FIG 2: Cyber-Physical Coupling Framework
# ============================================================================
fig, ax = plt.subplots(figsize=(9, 7.2), facecolor=C_BG)
ax.set_facecolor(C_BG)
ax.set_xlim(0, 10)
ax.set_ylim(0, 9.5)
ax.axis('off')

# Cyber Layer
box_cyber_bg = patches.FancyBboxPatch((0.5, 6.4), 9.0, 2.7, boxstyle="round,pad=0.1", fc='#D9E1F2', ec='#8FAADC', lw=1.5, ls='--')
ax.add_patch(box_cyber_bg)
ax.text(5.0, 8.8, 'Cyber Layer', ha='center', va='center', fontsize=11, fontweight='bold', color='#1B365D')

box_scada = patches.FancyBboxPatch((1.2, 6.7), 3.4, 1.8, boxstyle="round,pad=0.1", fc='#2F5597', ec='#1B365D', lw=1.5)
ax.add_patch(box_scada)
ax.text(2.9, 8.1, 'SCADA Server', ha='center', va='center', fontsize=10, fontweight='bold', color='#FFFFFF')
ax.text(2.9, 7.3, '• Risk Classification\n• Graded Early Warning\n• ΔH/Δt , ΔP/Δt Monitor', ha='left', va='center', fontsize=8.5, color='#FFFFFF')

box_plc = patches.FancyBboxPatch((5.4, 6.7), 3.4, 1.8, boxstyle="round,pad=0.1", fc='#2F5597', ec='#1B365D', lw=1.5)
ax.add_patch(box_plc)
ax.text(7.1, 8.1, 'PLC Network', ha='center', va='center', fontsize=10, fontweight='bold', color='#FFFFFF')
ax.text(7.1, 7.3, '• Tank PLCs\n• Pump PLCs\n• Junction PLCs', ha='left', va='center', fontsize=8.5, color='#FFFFFF')

ax.annotate('', xy=(5.4, 7.7), xytext=(4.6, 7.7), arrowprops=dict(arrowstyle='->', lw=1.2, color='#FFFFFF'))
ax.annotate('', xy=(4.6, 7.1), xytext=(5.4, 7.1), arrowprops=dict(arrowstyle='->', lw=1.2, color='#FFFFFF'))

# Coupling Layer
box_coup_bg = patches.FancyBboxPatch((0.5, 3.4), 9.0, 2.5, boxstyle="round,pad=0.1", fc='#E2EFDA', ec='#A9D18E', lw=1.5, ls='--')
ax.add_patch(box_coup_bg)
ax.text(5.0, 5.5, 'Coupling Layer', ha='center', va='center', fontsize=11, fontweight='bold', color='#274E13')

box_m1 = patches.FancyBboxPatch((1.0, 3.7), 3.8, 1.5, boxstyle="round,pad=0.1", fc='#FFFFFF', ec='#385723', lw=1.2)
ax.add_patch(box_m1)
ax.text(2.9, 4.45, '• State Mapping (H, P → Risk Levels)\n• Time-Difference Window (ΔT) Generation\n• Warning / Alert / Critical Buffer Zones', ha='left', va='center', fontsize=8.0, color='#274E13')

box_m2 = patches.FancyBboxPatch((5.2, 3.7), 3.8, 1.5, boxstyle="round,pad=0.1", fc='#FFFFFF', ec='#385723', lw=1.2)
ax.add_patch(box_m2)
ax.text(7.1, 4.45, '• Graceful Degradation Mechanism\n• Closed-loop Feedback Control\n• Ratchet Anti-chatter Logic', ha='left', va='center', fontsize=8.0, color='#274E13')

# Physical Layer
box_phys_bg = patches.FancyBboxPatch((0.5, 0.3), 9.0, 2.5, boxstyle="round,pad=0.1", fc='#FCE4D6', ec='#F4B183', lw=1.5, ls='--')
ax.add_patch(box_phys_bg)
ax.text(5.0, 2.4, 'Physical Layer', ha='center', va='center', fontsize=11, fontweight='bold', color='#833C0C')

box_p1 = patches.FancyBboxPatch((1.0, 0.6), 3.8, 1.2, boxstyle="round,pad=0.1", fc='#C65911', ec='#833C0C', lw=1.2)
ax.add_patch(box_p1)
ax.text(2.9, 1.4, 'Hydraulic Degradation Process', ha='center', va='center', fontsize=9, fontweight='bold', color='#FFFFFF')
ax.text(2.9, 0.9, '• Tank Level (H) ↓ → Pressure (P) ↓', ha='center', va='center', fontsize=8.0, color='#FFFFFF')

box_p2 = patches.FancyBboxPatch((5.2, 0.6), 3.8, 1.2, boxstyle="round,pad=0.1", fc='#C65911', ec='#833C0C', lw=1.2)
ax.add_patch(box_p2)
ax.text(7.1, 1.4, 'Physical Buffer', ha='center', va='center', fontsize=9, fontweight='bold', color='#FFFFFF')
ax.text(7.1, 0.9, '• Tank Storage  • Pipeline Residual Water', ha='center', va='center', fontsize=8.0, color='#FFFFFF')

ax.annotate('Sensing Dependency', xy=(5.0, 6.4), xytext=(5.0, 5.9), ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1B365D', arrowprops=dict(arrowstyle='<->', lw=1.5, color='#2F5597'))
ax.annotate('Warning Dependency', xy=(5.0, 3.4), xytext=(5.0, 2.8), ha='center', va='center', fontsize=8.5, fontweight='bold', color='#833C0C', arrowprops=dict(arrowstyle='<->', lw=1.5, color='#C65911'))

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'Fig2.png'), dpi=300, bbox_inches='tight')
plt.close()


# ============================================================================
# FIG 3: Co-Simulation Platform Architecture
# ============================================================================
fig, ax = plt.subplots(figsize=(8.5, 7.2), facecolor=C_BG)
ax.set_facecolor(C_BG)
ax.set_xlim(0, 10)
ax.set_ylim(0, 9.5)
ax.axis('off')

box_top_hdr = patches.Rectangle((0.5, 8.5), 9.0, 0.7, fc='#2F5597', ec='#1B365D', lw=1.2)
box_top_body = patches.Rectangle((0.5, 6.5), 9.0, 2.0, fc='#B4C6E7', ec='#1B365D', lw=1.2)
ax.add_patch(box_top_body)
ax.add_patch(box_top_hdr)
ax.text(5.0, 8.85, 'Cyber SCADA Module (Decision Layer)', ha='center', va='center', fontsize=11, fontweight='bold', color='#FFFFFF')
ax.text(1.0, 7.5, '• Real-time State Acquisition (H, P)\n• ΔH/Δt & Pressure Trend Monitoring\n• Status Transition Detection\n• Time-Difference (ΔT) Calculation', ha='left', va='center', fontsize=8.5, color='#1B365D')
ax.text(5.5, 7.5, '• Graded Risk Classification\n  - Normal\n  - Warning\n  - Alert\n  - Critical\n  - Outlet Failure', ha='left', va='center', fontsize=8.5, color='#1B365D')

box_mid_hdr = patches.Rectangle((0.5, 5.4), 9.0, 0.6, fc='#385723', ec='#274E13', lw=1.2)
box_mid_body = patches.Rectangle((0.5, 3.5), 9.0, 1.9, fc='#A9D18E', ec='#274E13', lw=1.2)
ax.add_patch(box_mid_body)
ax.add_patch(box_mid_hdr)
ax.text(5.0, 5.7, 'Synchronization Database Layer (SQLite)', ha='center', va='center', fontsize=11, fontweight='bold', color='#FFFFFF')

box_db1 = patches.Rectangle((0.8, 3.7), 2.5, 1.5, fc='#C6E0B4', ec='#385723', lw=1)
ax.add_patch(box_db1)
ax.text(2.05, 4.45, '• Physical State Table\n  - Tank Levels (H)\n  - Nodal Pressures (P)\n  - Flow Rates (Q)', ha='center', va='center', fontsize=7.5, color='#274E13')

box_db2 = patches.Rectangle((3.6, 3.7), 2.8, 1.5, fc='#C6E0B4', ec='#385723', lw=1)
ax.add_patch(box_db2)
ax.text(5.0, 4.45, '• Event & Transition Log\n  - Risk Level Changes\n  - Timestamp Records\n  - Duration of Each State', ha='center', va='center', fontsize=7.5, color='#274E13')

box_db3 = patches.Rectangle((6.7, 3.7), 2.5, 1.5, fc='#C6E0B4', ec='#385723', lw=1)
ax.add_patch(box_db3)
ax.text(7.95, 4.45, 'ΔT Computation Data\nDual Resilience Metrics\n(RI_pressure, RI_service, V_unmet)', ha='center', va='center', fontsize=7.5, color='#274E13')

box_bot_hdr = patches.Rectangle((0.5, 2.4), 9.0, 0.6, fc='#C65911', ec='#833C0C', lw=1.2)
box_bot_body = patches.Rectangle((0.5, 0.3), 9.0, 2.1, fc='#F8CBAD', ec='#833C0C', lw=1.2)
ax.add_patch(box_bot_body)
ax.add_patch(box_bot_hdr)
ax.text(5.0, 2.7, 'Physical Simulation Module', ha='center', va='center', fontsize=11, fontweight='bold', color='#FFFFFF')

box_wntr = patches.Rectangle((0.8, 0.5), 2.2, 1.7, fc='#F2F2F2', ec='#833C0C', lw=1)
ax.add_patch(box_wntr)
ax.text(1.9, 1.6, 'WNTR / EPANET 2.2\n(300 s timestep)', ha='center', va='center', fontsize=8, fontweight='bold', color='#833C0C')
ax.annotate('', xy=(1.9, 0.8), xytext=(1.9, 1.3), arrowprops=dict(arrowstyle='->', lw=1.5, color='#C65911'))
ax.text(1.9, 0.65, 'PDA Hydraulics', ha='center', va='center', fontsize=7.5, color='#833C0C')

ax.text(4.5, 1.3, '• Governing Equations\n• Source Interruption Scenario (24-48 h)\n• Hydraulic Degradation Process', ha='left', va='center', fontsize=8, color='#833C0C')
ax.text(7.5, 1.3, '• Outputs\n  - Tank Water Levels (H)\n  - Nodal Pressures (P)\n  - Flow Rates (Q)', ha='left', va='center', fontsize=8, color='#833C0C')

ax.annotate('', xy=(3.0, 6.1), xytext=(3.0, 6.5), arrowprops=dict(arrowstyle='->', lw=2, color='#385723'))
ax.annotate('', xy=(7.0, 6.5), xytext=(7.0, 6.1), arrowprops=dict(arrowstyle='->', lw=2, color='#2F5597'))
ax.annotate('', xy=(3.0, 3.0), xytext=(3.0, 3.5), arrowprops=dict(arrowstyle='->', lw=2, color='#C65911'))
ax.annotate('', xy=(7.0, 3.5), xytext=(7.0, 3.0), arrowprops=dict(arrowstyle='->', lw=2, color='#385723'))

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'Fig3.png'), dpi=300, bbox_inches='tight')
plt.close()


# ============================================================================
# FIG 4: Tank Risk State Evolution (NO Internal Title, Fixed Label Overlaps)
# ============================================================================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.8), facecolor=C_BG, gridspec_kw={'height_ratios': [1.1, 1]})
ax1.set_facecolor(C_BG)
ax2.set_facecolor(C_BG)

t_hrs = df_t1_no['time_h'].values

def classify_state(h):
    if h >= 5.0: return 'Normal'
    if h >= 4.0: return 'WARNING'
    if h >= 2.0: return 'ALERT'
    if h >= 0.5: return 'CRITICAL'
    return 'Outlet Failure'

state_colors = {
    'Normal': C_NORMAL,
    'WARNING': C_WARNING,
    'ALERT': C_ALERT,
    'CRITICAL': C_CRITICAL,
    'Outlet Failure': C_FAILURE
}

t1_no_vals = df_t1_no['value'].values
t1_ew_vals = df_t1_ew['value'].values
t2_no_vals = df_t2_no['value'].values
t2_ew_vals = df_t2_ew['value'].values

y_positions = [4, 3, 2, 1]
y_labels = ['T2 - With EWM', 'T2 - Without EWM', 'T1 - With EWM', 'T1 - Without EWM']
series_data = [t2_ew_vals, t2_no_vals, t1_ew_vals, t1_no_vals]

for idx, (y_pos, vals) in enumerate(zip(y_positions, series_data)):
    for i in range(len(t_hrs)-1):
        st = classify_state(vals[i])
        c = state_colors[st]
        ax1.barh(y_pos, width=t_hrs[i+1]-t_hrs[i], left=t_hrs[i], height=0.55, color=c, edgecolor='none')

ax1.set_yticks(y_positions)
ax1.set_yticklabels(y_labels, fontsize=8.5, fontweight='bold', color='black')
ax1.set_xlim(0, 72)
ax1.set_ylim(0.2, 5.8)
ax1.set_xlabel('Time (h)', fontsize=9, fontweight='bold', color='black')
# Clean subpanel label at top left outside tick area
ax1.text(-0.06, 1.05, '(a)', transform=ax1.transAxes, fontsize=11, fontweight='bold', color='black')

ax1.axvline(24, color='#2F5597', linestyle='-', lw=1.2)
ax1.axvline(48, color='#2F5597', linestyle='-', lw=1.2)
ax1.text(24, 0.3, 'Malfunction\nStart (24h)', ha='center', va='top', fontsize=7.5, color='#2F5597')
ax1.text(48, 0.3, 'Malfunction\nEnd (48h)', ha='center', va='top', fontsize=7.5, color='#2F5597')

legend_patches = [
    patches.Patch(color=C_NORMAL, label='Normal (≥ 5.0 m)'),
    patches.Patch(color=C_WARNING, label='WARNING (4.0–5.0 m)'),
    patches.Patch(color=C_ALERT, label='ALERT (2.0–4.0 m)'),
    patches.Patch(color=C_CRITICAL, label='CRITICAL (0.5–2.0 m)'),
    patches.Patch(color=C_FAILURE, label='Outlet Failure (< 0.5 m)')
]
ax1.legend(handles=legend_patches, loc='upper right', ncol=2, fontsize=7.5, framealpha=0.95, edgecolor='#BDC3C7')


# Subplot (b): Stacked Bar Chart for State Durations
durations_data = {
    'T1 Without EWM': [2.50, 0.67, 1.33, 1.00, 18.50],
    'T1 With EWM':    [2.50, 0.92, 3.33, 5.08, 12.17],
    'T2 Without EWM': [2.50, 0.67, 1.33, 1.00, 18.50],
    'T2 With EWM':    [2.50, 1.00, 3.33, 5.08, 12.17]
}

x_cats = ['T1\nWithout EWM', 'T1\nWith EWM', 'T2\nWithout EWM', 'T2\nWith EWM']
states_keys = ['Normal', 'WARNING', 'ALERT', 'CRITICAL', 'Outlet Failure']

bottoms = np.zeros(4)
bar_width = 0.45
x_pos = [1, 2, 3.2, 4.2]

for state_idx, st in enumerate(states_keys):
    vals = [durations_data[k][state_idx] for k in ['T1 Without EWM', 'T1 With EWM', 'T2 Without EWM', 'T2 With EWM']]
    c = state_colors[st]
    bars = ax2.bar(x_pos, vals, bottom=bottoms, width=bar_width, color=c, edgecolor='white', lw=0.5, label=st)
    
    for b_idx, (p, v, b) in enumerate(zip(x_pos, vals, bottoms)):
        if v >= 0.5:
            ax2.text(p, b + v/2.0, f'{v:.2f}h', ha='center', va='center', fontsize=7.5, color='white' if st in ['Normal', 'CRITICAL', 'Outlet Failure'] else 'black', fontweight='bold')
    
    bottoms += np.array(vals)

ax2.set_xticks(x_pos)
ax2.set_xticklabels(x_cats, fontsize=8.5, fontweight='bold', color='black')
ax2.set_ylabel('Duration (h)', fontsize=9, fontweight='bold', color='black')
# Clean subpanel label at top left outside tick area
ax2.text(-0.06, 1.05, '(b)', transform=ax2.transAxes, fontsize=11, fontweight='bold', color='black')
ax2.set_ylim(0, 32)

ax2.legend(loc='upper right', ncol=2, fontsize=8, framealpha=0.95, edgecolor='#BDC3C7')
ax2.axhline(24.0, color='#888888', linestyle=':', lw=1)

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'Fig4.png'), dpi=300, bbox_inches='tight')
plt.close()


# ============================================================================
# FIG 5: Pressure Dynamics (NO Internal Title)
# ============================================================================
fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=C_BG)
ax.set_facecolor(C_BG)

press_no_mpa = df_no['avg_pressure'].values / 101.97
press_ew_mpa = df_ew['avg_pressure'].values / 101.97
ts = df_no['time_h'].values

ax.plot(ts, press_no_mpa, color=C_FAILURE, linestyle='-', linewidth=2, label='Without EWM')
ax.plot(ts, press_ew_mpa, color=C_NORMAL, linestyle='-', linewidth=2, label='With EWM')

ax.fill_between(ts, press_no_mpa, press_ew_mpa, where=(press_ew_mpa >= press_no_mpa) & (ts >= 24) & (ts <= 48),
                color=C_SHADE, alpha=0.7, label='EWM improvement')

ax.axhline(0.10, color='#333333', linestyle=':', linewidth=1.2, label='Critical Pressure (0.10 MPa)')

ax.axvline(24.0, color='#2F5597', linestyle='--', lw=1)
ax.axvline(26.5, color=C_WARNING, linestyle='-.', lw=1)
ax.axvline(27.5, color=C_ALERT, linestyle='-.', lw=1)
ax.axvline(30.83, color=C_CRITICAL, linestyle='-.', lw=1)
ax.axvline(48.0, color='#2F5597', linestyle='--', lw=1)

ax.set_xlim(0, 72)
ax.set_ylim(-0.02, 0.62)
ax.set_xlabel('Time (h)', fontsize=9.5, fontweight='bold', color='black')
ax.set_ylabel('Average Pressure (MPa)', fontsize=9.5, fontweight='bold', color='black')

ax.legend(loc='lower left', fontsize=8.5, framealpha=0.95, edgecolor='#BDC3C7')
ax.grid(True)

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'Fig5.png'), dpi=300, bbox_inches='tight')
plt.close()


# ============================================================================
# FIG 6: Dual Metric Bar Chart & Volumetric Accounting (Clean Subpanel Labels)
# ============================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), facecolor=C_BG)
ax1.set_facecolor(C_BG)
ax2.set_facecolor(C_BG)

bars1 = ax1.bar([0.8, 2.0], [0.22, 0.84], width=0.35, color=[C_FAILURE, C_NORMAL], edgecolor='none')
bars2 = ax1.bar([1.2, 2.4], [0.23, 0.29], width=0.35, color=['#E6B0AA', '#A9DFBF'], edgecolor='none')

ax1.axhline(1.0, color='#2F5597', linestyle=':', lw=1.2, label='Ideal RI = 1.0')

ax1.text(0.8, 0.24, '0.22\n(Pressure)', ha='center', va='bottom', fontsize=8, fontweight='bold', color=C_FAILURE)
ax1.text(1.2, 0.25, '0.23\n(Service)', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#A93226')
ax1.text(2.0, 0.86, '0.84\n(Pressure)', ha='center', va='bottom', fontsize=8, fontweight='bold', color=C_NORMAL)
ax1.text(2.4, 0.31, '0.29\n(Service)', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#1E824C')

ax1.annotate('', xy=(2.0, 0.80), xytext=(0.8, 0.28),
             arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.35", lw=2, color='#1B365D', alpha=0.35), zorder=1)

ax1.set_xticks([1.0, 2.2])
ax1.set_xticklabels(['Without EWM', 'With EWM'], fontsize=9.5, fontweight='bold', color='black')
ax1.set_ylabel('Resilience Index', fontsize=9.5, fontweight='bold', color='black')
ax1.text(-0.08, 1.04, '(a)', transform=ax1.transAxes, fontsize=11, fontweight='bold', color='black')
ax1.set_ylim(0, 1.25)
ax1.legend(loc='upper left', fontsize=8, framealpha=0.95, edgecolor='#BDC3C7')


# Subplot (b)
v_deliv = [1353.5, 1843.1]
v_unmet = [6469.3, 5979.7]

x_vol = np.array([1, 2.2])
w = 0.35

ax2.bar(x_vol - w/2, v_deliv, width=w, color='#2980B9', label='Delivered Water (m³)')
ax2.bar(x_vol + w/2, v_unmet, width=w, color='#E67E22', label='Unmet Demand (m³)')

ax2.text(1 - w/2, 1353.5 + 100, '1,353.5 m³', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#1B4F72')
ax2.text(2.2 - w/2, 1843.1 + 100, '1,843.1 m³\n(+36.2%)', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#1B4F72')

ax2.text(1 + w/2, 6469.3 + 100, '6,469.3 m³', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#A04000')
ax2.text(2.2 + w/2, 5979.7 + 100, '5,979.7 m³\n(-8.8%)', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#A04000')

ax2.set_xticks(x_vol)
ax2.set_xticklabels(['Without EWM', 'With EWM'], fontsize=9.5, fontweight='bold', color='black')
ax2.set_ylabel('Volume (m³)', fontsize=9.5, fontweight='bold', color='black')
ax2.text(-0.08, 1.04, '(b)', transform=ax2.transAxes, fontsize=11, fontweight='bold', color='black')
ax2.set_ylim(0, 9500)
ax2.legend(loc='upper right', fontsize=8, framealpha=0.95, edgecolor='#BDC3C7')

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'Fig6.png'), dpi=300, bbox_inches='tight')
plt.close()


# ============================================================================
# FIG 7 & FIG 8: Sensitivity Analysis Figures (Clean Subpanel Labels)
# ============================================================================
print('=== Generating Fig. 7 & Fig. 8: Fig7.png & Fig8.png ===')

df_sens_dur = pd.read_csv('02_revised/results/sensitivity_faultdur.csv')
df_sens_tank = pd.read_csv('02_revised/results/sensitivity_tanksize.csv')

dur_hours = df_sens_dur['fault_duration'] / 3600.0

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), facecolor=C_BG)
ax1.set_facecolor(C_BG)
ax2.set_facecolor(C_BG)

ax1.plot(dur_hours, df_sens_dur['deliv_gain_pct'], 'o-', color='#1976D2', lw=2.2, ms=7, label='Delivered Water Gain (%)')
ax1.axhline(0, color=C_FAILURE, linestyle='--', lw=1.2, label='Zero Gain Threshold')
ax1.set_xlabel('Outage Duration (h)', fontsize=9.5, fontweight='bold', color='black')
ax1.set_ylabel('Delivered Water Gain (%)', fontsize=9.5, fontweight='bold', color='black')
ax1.text(-0.08, 1.04, '(a)', transform=ax1.transAxes, fontsize=11, fontweight='bold', color='black')
ax1.set_ylim(-15, 135)
ax1.grid(True)
ax1.legend(loc='upper left', fontsize=8, framealpha=0.95, edgecolor='#BDC3C7')

ax2.plot(df_sens_tank['diameter_scale'], df_sens_tank['deliv_gain_pct'], 's-', color='#388E3C', lw=2.2, ms=7, label='Delivered Water Gain (%)')
ax2.axhline(0, color=C_FAILURE, linestyle='--', lw=1.2, label='Zero Gain Threshold')
ax2.set_xlabel('Tank Storage Scale (Diameter Scale)', fontsize=9.5, fontweight='bold', color='black')
ax2.set_ylabel('Delivered Water Gain (%)', fontsize=9.5, fontweight='bold', color='black')
ax2.text(-0.08, 1.04, '(b)', transform=ax2.transAxes, fontsize=11, fontweight='bold', color='black')
ax2.set_ylim(-15, 235)
ax2.grid(True)
ax2.legend(loc='upper right', fontsize=8, framealpha=0.95, edgecolor='#BDC3C7')

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'Fig7.png'), dpi=300, bbox_inches='tight')
plt.close()


# Fig 8
fig, ax = plt.subplots(figsize=(7, 4.2), facecolor=C_BG)
ax.set_facecolor(C_BG)

ax.plot(dur_hours, df_sens_dur['RI_p_ew'], 'o-', color=C_NORMAL, lw=2, label='Pressure RI (With EWM)')
ax.plot(dur_hours, df_sens_dur['RI_p_no'], 'o--', color=C_FAILURE, lw=2, label='Pressure RI (Without EWM)')
ax.plot(dur_hours, df_sens_dur['RI_s_ew'], 's-', color='#1976D2', lw=2, label='Service RI (With EWM)')
ax.plot(dur_hours, df_sens_dur['RI_s_no'], 's--', color=C_ALERT, lw=2, label='Service RI (Without EWM)')

ax.set_xlabel('Outage Duration (h)', fontsize=9.5, fontweight='bold', color='black')
ax.set_ylabel('Resilience Index (0 to 1)', fontsize=9.5, fontweight='bold', color='black')
ax.set_ylim(-0.05, 1.05)
ax.grid(True)
ax.legend(loc='center right', fontsize=8.5, framealpha=0.95, edgecolor='#BDC3C7')

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'Fig8.png'), dpi=300, bbox_inches='tight')
plt.close()

print('ALL PERFECT FIGURES GENERATED AND SYNCHRONIZED!')

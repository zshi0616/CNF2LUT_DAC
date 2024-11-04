import numpy as np 
import glob
import os 
import itertools
import copy
import time
from collections import Counter

from utils.utils import run_command
import utils.cnf_utils as cnf_utils
import utils.clut_utils as clut_utils
import utils.circuit_utils as circuit_utils
import utils.convert_utils as convert_utils
from utils.simulator import dec2list, list2hex
from itertools import combinations

import sys
sys.setrecursionlimit(100000)

# cnf_dir = '/home/zyshi21/studio/dataset/sat_2023'
cnf_dir = './testcase'
NAME_LIST = [
    # 'a26',
    # "brent_9_0"
    # '27b4fe4cb0b4e2fd8327209ca5ff352c-grid_10_20'
]

DEBUG = False
LUT_MAX_FANIN = 6
gate_to_index={'PI': 0, 'LUT': 1}
output_dir = './tmp/'

def cnf2lut(
    cnf, no_vars, 
    partial_convert=False, 
):
    # Divide long clause
    cnf, no_vars = convert_utils.divide_long_clauses(cnf, no_vars, max_length=LUT_MAX_FANIN-1)
    no_clauses = len(cnf)
    
    x_data = []
    fanin_list = []
    fanout_list = []
    has_lut = [False] * no_vars
    clause_visited = [False] * no_clauses
    extra_po = []
    extra_pi = []
    po_list = []
    map_inv_idx = {}
    
    # Preprocess 
    var_comb_map, var2varcomb_map = convert_utils.get_var_comb_map(cnf, max_length=LUT_MAX_FANIN-1)
    for k in range(1, no_vars + 1):
        x_data.append([k-1, gate_to_index['PI'], ''])
        fanin_list.append([])
        fanout_list.append([])
    
    # Convert 
    for clause_idx, clause in enumerate(cnf):
        if clause_visited[clause_idx]:
            continue
        lut_queue = []
        has_converted = False
        for var in clause:
            if not has_lut[abs(var) - 1]:
                po_var = abs(var)
                po_idx = po_var - 1
                lut_queue = [po_idx]
                has_lut[po_idx] = True
                po_list.append(po_idx)
                has_converted = True
                break
        
        # BFS to generate LUT 
        while len(lut_queue) > 0:
            lut_idx = lut_queue.pop(0)
            lut_idx_list = []
            var_comb, cover_clauses, tt = convert_utils.select_cnf(cnf, clause_visited, lut_idx, var_comb_map, var2varcomb_map, max_fanin=LUT_MAX_FANIN)

            if len(var_comb) == 0:
                if len(tt) == 1:
                    const = tt[0]
                    if const == 1:
                        x_data[lut_idx] = [lut_idx, 'vdd', '']
                    else:
                        x_data[lut_idx] = [lut_idx, 'gnd', '']
                    clause_visited[cover_clauses[0]] = 1
            elif sum(tt) == len(tt):
                # All 1s 
                x_data[lut_idx] = [lut_idx, 'vdd', '']
                for clause_idx in cover_clauses:
                    clause_visited[clause_idx] = 1
            elif sum(tt) == 0:
                # All 0s 
                x_data[lut_idx] = [lut_idx, 'gnd', '']
                for clause_idx in cover_clauses:
                    clause_visited[clause_idx] = 1
            else:        
                # Generate LUT 
                lut_fanin_list = []
                for var in var_comb:
                    lut_fanin_list.append(var-1)
                
                for idx in lut_fanin_list:
                    if not has_lut[idx]:
                        lut_queue.append(idx)
                        has_lut[idx] = True
                        
                # Parse 3-lut tt: 2 - Don't Care / -1 - Not Available State 
                if 2 in tt:
                    new_fanin_idx = len(x_data)
                    extra_pi.append(len(x_data))
                    x_data.append([new_fanin_idx, gate_to_index['PI'], ''])
                    fanin_list.append([])
                    fanout_list.append([])
                    lut_fanin_list.append(new_fanin_idx)
                    new_tt = []
                    for k in range(len(tt)):
                        if tt[k] == 2:
                            new_tt.append(0)
                            new_tt.append(1)
                        else:
                            new_tt.append(tt[k])
                            new_tt.append(tt[k])
                    tt = new_tt
                if -1 in tt:
                    add_fanout_tt = [1] * len(tt)
                    for k in range(len(tt)):
                        if tt[k] == -1:
                            add_fanout_tt[k] = 0
                            tt[k] = 0       # 2 means don't care, if unsupport in LUT parser, use 0 
                    new_fanout_idx = len(x_data)
                    extra_po.append(new_fanout_idx)
                    tt_hex, ordered_lut_fanin_idx = convert_utils.create_lut(add_fanout_tt, lut_fanin_list)
                    x_data.append([new_fanout_idx, gate_to_index['LUT'], tt_hex])
                    fanout_list.append([])
                    fanin_list.append([])
                    fanin_list[new_fanout_idx] = ordered_lut_fanin_idx
                    for fanin_idx in ordered_lut_fanin_idx:
                        fanout_list[fanin_idx].append(new_fanout_idx)
                
                if len(tt) == 2 and tt[0] == 0 and tt[1] == 1:
                    if lut_fanin_list[0] not in map_inv_idx:
                        map_inv_idx[lut_fanin_list[0]] = lut_idx
                tt_hex, ordered_lut_fanin_idx = convert_utils.create_lut(tt, lut_fanin_list)
                x_data[lut_idx] = [lut_idx, gate_to_index['LUT'], tt_hex]

                fanin_list[lut_idx] = ordered_lut_fanin_idx
                for fanin_idx in ordered_lut_fanin_idx:
                    fanout_list[fanin_idx].append(lut_idx)
                lut_idx_list.append(lut_idx)
                    
                for clause_idx in cover_clauses:
                    clause_visited[clause_idx] = 1
        
        if DEBUG and has_converted:
            print('[DEBUG] CNF2LUT Convert Ratio: {:} / {:} = {:.2f}%, # Circuit: {:}'.format(
                np.sum(clause_visited), len(clause_visited), np.sum(clause_visited) / len(clause_visited) * 100, 
                len(po_list)
            ))
    
    # Uncovered
    if partial_convert:
        unconverted_cnf = []
        for clause_k in range(len(clause_visited)):
            if clause_visited[clause_k] == 0:
                unconverted_cnf.append(cnf[clause_k])
    else:
        unconverted_cnf = []
        for clause_k in range(len(clause_visited)):
            if clause_visited[clause_k] == 0:
                # print('[INFO] Find unassigned clauses, append to PO')
                unassigned_clause = cnf[clause_k]
                
                # Now just append unconnected clauses to PO 
                extra_or_list = []
                for var in unassigned_clause:
                    node_idx = abs(var) - 1
                    if var > 0:
                        extra_or_list.append(node_idx)
                    elif node_idx in map_inv_idx:
                        extra_or_list.append(map_inv_idx[node_idx])
                    else:
                        extra_not = len(x_data)
                        x_data.append([extra_not, gate_to_index['LUT'], '1'])
                        fanin_list.append([node_idx])
                        fanout_list.append([])
                        map_inv_idx[node_idx] = extra_not
                        extra_or_list.append(map_inv_idx[node_idx])
                x_data, fanin_list, fanout_list, or_idx = convert_utils.add_extra_or(x_data, fanin_list, fanout_list, extra_or_list, gate_to_index)
                extra_po.append(or_idx)
    
    
    # Check loop 
    visited = []
    for idx in range(no_vars):
        visited.append([False] * len(fanin_list[idx]))
            
    convert_utils.traverse_graph(
        no_vars, x_data, visited, fanin_list, fanout_list, extra_pi, extra_po, po_list, gate_to_index
    ) # last_node initialized as po_idx
    
    # Finish converting 
    # print('Finish converting')
    return x_data, fanin_list, po_list, extra_pi, extra_po, unconverted_cnf
    

def main(cnf_path, output_bench_path):
    # Read CNF 
    cnf, no_vars = cnf_utils.read_cnf(cnf_path)
    
    # Main 
    convert_starttime = time.time()
    x_data, fanin_list, po_list, extra_pi, extra_po, unconverted_cnf = cnf2lut(cnf, no_vars, partial_convert=False)
    print('convert time: {:.4f} s'.format(time.time() - convert_starttime))
    
    # Save 
    fanout_list = clut_utils.get_fanout_list(x_data, fanin_list)
    saveclut_starttime = time.time()
    
    clut_utils.save_clut(output_bench_path, x_data, fanin_list, fanout_list, const_1_list=extra_po)
    print('saveclut time: {:.4f} s'.format(time.time() - saveclut_starttime))

if __name__ == '__main__':
    DEBUG = True
    
    for cnf_path in glob.glob(os.path.join(cnf_dir, '*.cnf')):
        cnf_name = cnf_path.split('/')[-1].split('.')[0]
        if cnf_name not in NAME_LIST:
            continue
        print('Processing %s' % cnf_path)
        output_path = os.path.join(output_dir, cnf_name + '.bench')
        
        main(cnf_path, output_path)    
        print(output_path)
        print()

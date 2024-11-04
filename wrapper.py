import numpy as np 
import os 
import copy
import glob
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.circuit_utils as circuit_utils
import utils.aiger_utils as aiger_utils
import utils.simulator as simulator
from utils.utils import run_command
import utils.clut_utils as clut_utils

# Change here !!! (default: main_deloop.py)
from top import cnf2lut
from top import main as cnf2lut_bench

import time 

import sys 
sys.setrecursionlimit(100000)

syn_recipe = 'source /home/zyshi21/opt/yosys/abc/abc.rc; strash; resyn2; '
map_recipe = 'source /home/zyshi21/opt/yosys/abc/abc.rc; strash; fraig; resyn2; '
mapper_path = './tools/mockturtle/build/examples/my_mapper'
cnf2aig_path = 'cnf2aig'

def cnf2lut_solve(cnf_path, verify=False, solver='kissat', timeout_args=''):
    cnf, no_var = cnf_utils.read_cnf(cnf_path)
    cnf = cnf_utils.sort_cnf(cnf)
    start_time = time.time()
    bench_x_data, bench_fanin_list, po_list, extra_pi, const_1_list, unconverted_cnf = cnf2lut(cnf, no_var, partial_convert=True)
    trans_time = time.time() - start_time
    
    # Parse Bench
    for idx in range(len(bench_x_data)):
        bench_x_data[idx] = ['N{:}'.format(idx), bench_x_data[idx][2]]
    bench_cnf = lut_utils.convert_cnf(bench_x_data, bench_fanin_list, const_1_list=const_1_list)
    
    # Solve without verification 
    if not verify:
        bench_cnf = bench_cnf + unconverted_cnf
        sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(bench_cnf, len(bench_x_data), args=timeout_args, solver=solver)
        return sat_status, asg, (trans_time, bench_solvetime)
    
def cnf2lut_samsat_solve(cnf_path, solver='kissat', timeout_args=''):     # TODO: Now only resyn2
    tmp_bench_path = './tmp/tmp_cases.bench'
    start_time = time.time()
    cnf, no_vars = cnf_utils.read_cnf(cnf_path)
    x_data, fanin_list, po_list, extra_pi, extra_po, unconverted_cnf = cnf2lut(cnf, no_vars, partial_convert=True)
    fanout_list = clut_utils.get_fanout_list(x_data, fanin_list)
    add_PO_flag = [False] * len(x_data)
    for clause in unconverted_cnf:
        for var in clause:
            add_PO_flag[abs(var)-1] = True
            
    clut_utils.save_clut(tmp_bench_path, x_data, fanin_list, fanout_list, const_1_list=extra_po, add_PO_flag=add_PO_flag)
    if not os.path.exists(tmp_bench_path):
        return -1, None, (0, 0)
    trans_time = time.time() - start_time
    
    # ABC 
    tmp_mapped_bench_path = './tmp/tmp_cases_mapped.bench'
    abc_cmd = 'abc -c "read_bench {}; {} write_bench {};"'.format(tmp_bench_path, map_recipe, tmp_mapped_bench_path)
    abc_out, abc_time = run_command(abc_cmd)
    for line in abc_out:
        assert 'Network contains a combinational loop' not in line
    trans_time += abc_time
    
    # Parse mapped bench 
    if not os.path.exists(tmp_mapped_bench_path):
        os.remove(tmp_bench_path)
        return -1, [], (trans_time, 1000)
    x_data, fanin_list, fanout_list, PI_list, PO_list = lut_utils.parse_bench(tmp_mapped_bench_path)
    
    # Old index to new index
    index_old2new = {}
    for idx, x_data_info in enumerate(x_data):
        if x_data_info[0][0] == 'N' and x_data_info[0][1:].isdigit():
            index_old2new[int(x_data_info[0][1:])] = idx
    new_unconverted_cnf = []
    for clause in unconverted_cnf:
        new_clause = []
        for var in clause:
            if var > 0:
                new_clause.append(index_old2new[var-1] + 1)
            else:
                new_clause.append(-1 * (index_old2new[abs(var)-1] + 1))
        new_unconverted_cnf.append(new_clause)
    
    # Parse constraints
    f = open(tmp_bench_path, 'r')
    lines = f.readlines()
    f.close()
    const_1_list = []
    for line in lines:
        if 'OUTPUT' in line and 'Const_1' in line:
            cell_index = int(line.split('(')[1].split(')')[0][1:])
            const_1_list.append(index_old2new[cell_index])
    
    # Construct CNF
    bench_cnf = lut_utils.convert_cnf(x_data, fanin_list, use_node_name=False, const_1_list=const_1_list)
    joint_cnf = bench_cnf + new_unconverted_cnf
    
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(joint_cnf, len(x_data), args=timeout_args, solver=solver)
    
    # Remove 
    os.remove(tmp_bench_path)
    os.remove(tmp_mapped_bench_path)
    
    return sat_status, asg, (trans_time, bench_solvetime)
    

def cnf2aig_solve(cnf_path, solver='kissat', timeout_args=''):
    tmp_aig_path = './tmp/tmp_cases.aig'
    cnf2aig_cmd = '{} {} {}'.format(cnf2aig_path, cnf_path, tmp_aig_path)
    _, trans_time = run_command(cnf2aig_cmd)
    
    # Parse AIG 
    x_data, edge_index = aiger_utils.aig_to_xdata(tmp_aig_path)
    fanin_list, fanout_list = circuit_utils.get_fanin_fanout(x_data, edge_index)
    PO_list = []
    for idx in range(len(fanout_list)):
        if len(fanout_list[idx]) == 0:
            PO_list.append(idx) 
    assert len(PO_list) == 1
    cnf = aiger_utils.aig_to_cnf(x_data, fanin_list, const_1=PO_list)
    no_vars = len(x_data)
    
    # solve 
    sat_status, asg, aig_solvetime = cnf_utils.kissat_solve(cnf, no_vars, args=timeout_args, solver=solver)
    
    # Remove
    os.remove(tmp_aig_path)
    
    return sat_status, asg, (trans_time, aig_solvetime)
    
def cnf2aig_samsat_solve(cnf_path, solver='kissat', timeout_args=''):
    tmp_aig_path = './tmp/tmp_cases.aig'
    cnf2aig_cmd = '{} {} {}'.format(cnf2aig_path, cnf_path, tmp_aig_path)
    _, trans_time = run_command(cnf2aig_cmd)
    
    # ABC 
    tmp_mapped_bench_path = './tmp/tmp_cases_mapped.bench'
    abc_cmd = 'abc -c "read_aiger {}; {} write_aiger {};"'.format(tmp_aig_path, syn_recipe, tmp_aig_path)
    _, abc_time = run_command(abc_cmd)
    trans_time += abc_time
    
    # Map 
    map_cmd = '{} {} {}'.format(mapper_path, tmp_aig_path, tmp_mapped_bench_path)
    _, map_time = run_command(map_cmd)
    trans_time += map_time
    
    # Solve 
    x_data, fanin_list, fanout_list, PI_list, PO_list = lut_utils.parse_bench(tmp_mapped_bench_path)
    assert len(PO_list) == 1
    bench_cnf = lut_utils.convert_cnf(x_data, fanin_list, const_1_list=PO_list)
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(bench_cnf, len(x_data), args=timeout_args, solver=solver)
    
    # Remove
    os.remove(tmp_aig_path)
    os.remove(tmp_mapped_bench_path)
    
    return sat_status, asg, (trans_time, bench_solvetime)

def baseline_solve(cnf_path, solver='kissat', timeout_args=''):
    res, _, st = cnf_utils.kissat_solve_file(cnf_path, args='{}'.format(timeout_args), solver=solver)
    return res, None, (0, st)
    
if __name__ == '__main__':
    print('[INFO] Debug wrapper.py ...')
    
    CASE_LIST = [
        'large_benchmark', 
        # 'mult_op_DEMO1_3_3_TOP6', 
        # 'a28', 
        # 'velev-pipe-o-uns-1-7', 
        # 'brent_15_0_25', 
    ]
    CNF_DIR = './case'
    
    if len(CASE_LIST) == 0:
        for case_path in glob.glob(os.path.join(CNF_DIR, '*.cnf')):
            case = os.path.basename(case_path)[:-4]
            CASE_LIST.append(case)
    
    for case_name in CASE_LIST:
        cnf_path = os.path.join(CNF_DIR, '{}.cnf'.format(case_name))
        if not os.path.exists(cnf_path):
            print('[WARNING] {:} not exists'.format(cnf_path))
            continue
    
        res, asg, time_list = cnf2lut_solve(cnf_path)
        # res, asg, time_list = cnf2lut_samsat_solve(cnf_path)
        
        print('[INFO] Case: {:}, Result: {:}'.format(case_name, res))
        print('Trans.: {:.2f}s, Solve: {:.2f}s'.format(time_list[0], time_list[1]))
        print()
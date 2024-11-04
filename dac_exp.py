import numpy as np 
import os 
import copy
import glob
import time 
import argparse
from wrapper import *

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case_dir', type=str, default='/home/zyshi21/studio/dataset/sat_2023')
    parser.add_argument('--solver', type=str, default='kissat')
    parser.add_argument('--case_hash_path', type=str, default='./hash/kissat.txt')
    parser.add_argument('--timeout_args', type=str, default='--time=1000')
    
    args = parser.parse_args()
    case_hash = []
    with open(args.case_hash_path, 'r') as f:
        for line in f:
            case_hash.append(line.strip())
    args.case_hash = case_hash
    
    return args

if __name__ == '__main__':
    args = get_args()
    tot_bl_time = 0
    tot_c2l_solvetime = 0
    tot_c2l_transtime = 0
    tot_c2lsam_solvetime = 0
    tot_c2lsam_transtime = 0
    
    # Read all cases and select for testing 
    case_list = []
    for case_path in glob.glob(os.path.join(args.case_dir, '*.cnf')):
        for case_hash in args.case_hash:
            if case_hash in case_path:
                case_list.append(case_path)
    print('[INFO] Total {:} cases'.format(len(case_list)))
    
    for cnf_path in case_list:
        case_name = os.path.basename(cnf_path)[:-4]
        if not os.path.exists(cnf_path):
            print('[WARNING] {:} not exists'.format(cnf_path))
            continue
        if os.stat(cnf_path).st_size > 10 * 1024 * 1024:
            print('[WARNING] {:} too large'.format(cnf_path))
            continue
        print('[INFO] Case: {:}'.format(case_name))
        
        ####################################################################
        # Baseline: CNF -> SAT
        ####################################################################
        bl_res, _, bl_timelist = baseline_solve(cnf_path, solver=args.solver, timeout_args=args.timeout_args)
        bl_time = bl_timelist[1]
        if bl_res == -1:
            print('[WARNING] Baseline Timeout')
        print('[INFO] Result: {:}'.format(bl_res))
        print('Baseline Time: {:.2f}s'.format(bl_timelist[1]))
        tot_bl_time += bl_time
        # bl_res = -1
        # bl_time = 1
        
        ####################################################################
        # C2L: CNF -> LUT -> CNF -> SAT
        ####################################################################
        c2l_res, _, c2l_timelist = cnf2lut_solve(cnf_path, verify=False, solver=args.solver, timeout_args=args.timeout_args)
        c2l_time = c2l_timelist[0] + c2l_timelist[1]
        if c2l_res == -1:
            print('[WARNING] c2l Timeout')
        print('[INFO] Result: {:}'.format(c2l_res))
        if bl_res != -1 and c2l_res != -1:
            # assert bl_res == c2l_res
            print('[ERROR] Baseline and C2L result not equal')
        print('[INFO] C2L Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
            c2l_timelist[0], c2l_timelist[1], c2l_time, 
            (bl_time - c2l_time) / bl_time * 100
        ))
        tot_c2l_solvetime += c2l_timelist[1]
        tot_c2l_transtime += c2l_timelist[0]
        
        # ####################################################################
        # # C2LSAM: CNF -> LUT -> SAM -> CNF -> SAT
        # ####################################################################
        c2lsam_res, _, c2lsam_timelist = cnf2lut_samsat_solve(cnf_path, solver=args.solver, timeout_args=args.timeout_args)
        c2lsam_time = c2lsam_timelist[0] + c2lsam_timelist[1]
        if c2lsam_res == -1:
            print('[WARNING] c2lsam Timeout')
        print('[INFO] Result: {:}'.format(c2lsam_res))
        if bl_res != -1 and c2lsam_res != -1:
            # assert c2lsam_res == bl_res
            print('[ERROR] Baseline and C2LSAM result not equal')
        print('[INFO] C2LSAM Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
            c2lsam_timelist[0], c2lsam_timelist[1], c2lsam_time, 
            (bl_time - c2lsam_time) / bl_time * 100
        ))
        tot_c2lsam_solvetime += c2lsam_timelist[1]
        tot_c2lsam_transtime += c2lsam_timelist[0]
        
        print()
    
    print()
    print('=' * 10 + ' PASS ' + '=' * 10)
    print('Total Baseline Time: {:.2f}s'.format(tot_bl_time))
    print('C2L Total Trans. Time: {:.2f}s, Solve Time: {:.2f}s'.format(
        tot_c2l_transtime, tot_c2l_solvetime
    ))
    print('C2L Total Time: {:.2f}s'.format(tot_c2l_transtime + tot_c2l_solvetime))
    print('C2LSAM Total Trans. Time: {:.2f}s, Solve Time: {:.2f}s'.format(
        tot_c2lsam_transtime, tot_c2lsam_solvetime
    ))
    print('C2LSAM Total Time: {:.2f}s'.format(tot_c2lsam_transtime + tot_c2lsam_solvetime))
'''
Utility functions for Look-up-table
Author: Stone
'''
import time
import copy
import numpy as np 
import os 

def read_file(file_name):
    f = open(file_name, "r")
    data = f.readlines()
    return data

def get_fanout_list(x_data, fanin_list):
    fanout_list = []
    for idx in range(len(x_data)):
        fanout_list.append([])
    for idx in range(len(x_data)):
        for fanin_idx in fanin_list[idx]:
            fanout_list[fanin_idx].append(idx)
    return fanout_list

def save_clut(filepath, x_data, fanin_list, fanout_list, const_1_list=[], add_PO_flag=[]):
    if len(add_PO_flag) == 0:
        add_PO_flag = [False] * len(x_data)
    pi_list = []
    po_list = []
    is_pi = [False] * len(x_data)
    is_po = [False] * len(x_data)
    for idx in range(len(x_data)):
        if len(fanin_list[idx]) == 0 and len(fanout_list[idx]) != 0:
            pi_list.append(idx)
            is_pi[idx] = True
        if (len(fanout_list[idx]) == 0 and len(fanin_list[idx]) != 0) or add_PO_flag[idx]:
            po_list.append(idx)
            is_po[idx] = True
    
    # Const_1 
    is_const_1 = [False] * len(x_data)
    for idx in const_1_list:
        is_const_1[idx] = True
    
    # Save 
    f = open(filepath, "w")
    for pi_idx in pi_list:
        f.write('INPUT(N' + str(pi_idx) + ')\n')
    for po_idx in po_list:
        if is_const_1[po_idx]:
            f.write('OUTPUT(N' + str(po_idx) + ')    # Const_1 \n')
        else:
            f.write('OUTPUT(N' + str(po_idx) + ')\n')
    for idx in range(len(x_data)):
        if is_const_1[idx] and not is_po[idx]:
            f.write('OUTPUT(N' + str(idx) + ')    # Const_1 \n')
    # for idx in range(len(x_data)):
    #     f.write('OUTPUT(N' + str(idx) + ')\n')
    
    # Save Gate 
    for idx in range(len(x_data)):
        if x_data[idx][1] == 'gnd':
            gate_line = 'N{} = gnd\n'.format(idx)
            f.write(gate_line)
        elif x_data[idx][1] == 'vdd':
            gate_line = 'N{} = vdd\n'.format(idx)
            f.write(gate_line)
        elif len(fanin_list[idx]) != 0:
            if x_data[idx][1] == 1:
                gate_line = 'N{} = LUT 0x{} ('.format(idx, x_data[idx][2])
            elif x_data[idx][1] == 2:
                gate_line = 'N{} = AND ('.format(idx)
            else:
                raise Exception('[ERROR] Unknown gate type {}'.format(x_data[idx][1]))
            for k, fanin_idx in enumerate(fanin_list[idx]):
                gate_line += 'N{}'.format(str(fanin_idx))
                if k != len(fanin_list[idx]) - 1:
                    gate_line += ', '
                else:
                    gate_line += ')\n'
            f.write(gate_line)
    
    f.close()
    
def check_equ(cnf, no_vars, x_data, fanin_list, fanout_list, po_list, const_1_list=[]):
    assert len(po_list) == 1
    
    pi_list = []
    for idx in range(len(x_data)):
        if len(fanin_list[idx]) == 0 and len(fanout_list[idx]) != 0:
            pi_list.append(idx)
    
    # Const_1 
    is_const_1 = [False] * len(x_data)
    for idx in const_1_list:
        is_const_1[idx] = True
    
    # Save 
    tmp_filepath = './tmp/tmp.bench'
    f = open(tmp_filepath, "w")
    for pi_idx in pi_list:
        f.write('INPUT(N' + str(pi_idx) + ')\n')
    for var_idx in range(no_vars):
        f.write('INPUT(VAR' + str(var_idx + 1) + ')\n')
    f.write('OUTPUT(PO)\n')
    f.write('\n')
    # for po_idx in po_list:
    #     if is_const_1[po_idx]:
    #         f.write('OUTPUT(N' + str(po_idx) + ')    # Const_1 \n')
    #     else:
    #         f.write('OUTPUT(N' + str(po_idx) + ')\n')
    # for idx in range(len(x_data)):
    #     if is_const_1[idx] and not is_po[idx]:
    #         f.write('OUTPUT(N' + str(idx) + ')    # Const_1 \n')
    # for idx in range(len(x_data)):
    #     f.write('OUTPUT(N' + str(idx) + ')\n')
    
    # Save Gate 
    for idx in range(len(x_data)):
        if len(fanin_list[idx]) != 0:
            if x_data[idx][1] == 1:
                gate_line = 'N{} = LUT 0x{} ('.format(idx, x_data[idx][2])
            elif x_data[idx][1] == 2:
                gate_line = 'N{} = AND ('.format(idx)
            else:
                raise Exception('[ERROR] Unknown gate type {}'.format(x_data[idx][1]))
            for k, fanin_idx in enumerate(fanin_list[idx]):
                gate_line += 'N{}'.format(str(fanin_idx))
                if k != len(fanin_list[idx]) - 1:
                    gate_line += ', '
                else:
                    gate_line += ')\n'
            f.write(gate_line)
    
    # Save clauses 
    for var in range(1, 1+no_vars):
        not_literal_line = 'VAR{}_NOT = NOT(VAR{})\n'.format(var, var)
        f.write(not_literal_line)
    for clause_idx, clause in enumerate(cnf):
        clause_line = 'CLAUSE{} = OR('.format(clause_idx)
        for var_idx, var in enumerate(clause):
            if var > 0:
                clause_line += 'VAR{}'.format(var)
            else:
                clause_line += 'VAR{}_NOT'.format(-var)
            if var_idx != len(clause) - 1:
                clause_line += ', '
            else:
                clause_line += ')\n'
        f.write(clause_line)
    po_line = 'CNF_PO = AND('
    for clause_idx in range(len(cnf)):
        po_line += 'CLAUSE{}'.format(clause_idx)
        if clause_idx != len(cnf) - 1:
            po_line += ', '
        else:
            po_line += ')\n'
    f.write(po_line)
    
    # Miter 
    miter_line = 'MITER = XOR(N{}, CNF_PO)\n'.format(po_list[0])
    f.write(miter_line)
    
    # PO 
    po_line = 'PO = AND(MITER, '
    for k, gate_idx in enumerate(const_1_list):
        po_line += 'N{}'.format(gate_idx)
        if k != len(const_1_list) - 1:
            po_line += ', '
        else:
            po_line += ')\n'
    f.write(po_line)
    f.close()
    
    # Check
    # print()
    
    
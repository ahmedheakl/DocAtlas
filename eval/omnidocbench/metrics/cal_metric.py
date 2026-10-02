import json
import os
import Levenshtein
from .table_metric import TEDS
from registry.registry import METRIC_REGISTRY
from utils.result_dir import result_path
from collections import defaultdict
import pandas as pd

def get_groups(samples, group_info):
    group_samples = defaultdict(list)
    for sample in samples:
        group_samples['all'].append(sample)
        for group in group_info:
            select_flag = True
            for k, v in group.items():
                for gt_attribute in sample['gt_attribute']:   # gt_attribute is a list containing all merged gt attributes
                    if not gt_attribute:   # if no GT attributes, don't include in calculation
                        select_flag = False
                    elif gt_attribute[k] != v:  # if any gt attribute doesn't meet criteria, don't select
                        select_flag = False
            if select_flag:
                group_samples[str(group)].append(sample)
    return group_samples


@METRIC_REGISTRY.register("TEDS")
class call_TEDS():
    def __init__(self, samples):
        self.samples = samples
    def evaluate(self, group_info=[], save_name='default'):
        teds = TEDS(structure_only=False)
        teds_structure_only = TEDS(structure_only=True)
        group_scores = defaultdict(list)
        group_scores_structure_only = defaultdict(list)
        samples = self.samples
        per_table_score = {}
        for sample in samples:
            gt = sample['norm_gt'] if sample.get('norm_gt') else sample['gt']
            pred = sample['norm_pred'] if sample.get('norm_pred') else sample['pred']
            try:
                score = teds.evaluate(pred, gt)
            except:
                score = 0
                print(f'TEDS score error for table {sample["gt_idx"]} in {sample["img_id"]}. The score is set to 0.')
            try:
                score_structure_only = teds_structure_only.evaluate(pred, gt)
            except:
                score_structure_only = 0
                print(f'TEDS_structure_only score error for table {sample["gt_idx"]} in {sample["img_id"]}. The score is set to 0.')
            # print('TEDS score:', score)
            group_scores['all'].append(score)
            group_scores_structure_only['all'].append(score_structure_only)
            if not sample.get('metric'):
                sample['metric'] = {}
            sample['metric']['TEDS'] = score
            sample['metric']['TEDS_structure_only'] = score_structure_only
            per_table_score[sample['img_id']+'_'+str(sample['gt_idx'])] = {'TEDS': score, 'TEDS_structure_only': score_structure_only}
            for group in group_info:
                select_flag = True
                for k, v in group.items():
                    for gt_attribute in sample['gt_attribute']:   # gt_attribute is a list containing all merged gt attributes
                        if not gt_attribute:   # if no GT attributes, don't include in calculation
                            select_flag = False
                        elif gt_attribute[k] != v:  # if any gt attribute doesn't meet criteria, don't select
                            select_flag = False
                if select_flag:
                    group_scores[str(group)].append(score)
        with open(result_path(f'{save_name}_per_table_TEDS.json'), 'w', encoding='utf-8') as f:
            json.dump(per_table_score, f, indent=4, ensure_ascii=False)
        result = {}
        for group_name, scores in group_scores.items():
            if len(scores) > 0:
                result[group_name] = sum(scores) / len(scores)    # average of normalized scores at sample level
            else:
                result[group_name] = 'NaN'
                print(f'Warning: Empyty matched samples for {group_name}.')
        
        structure_only_result = {}
        for group_name, scores in group_scores_structure_only.items():
            if len(scores) > 0:
                structure_only_result[group_name] = sum(scores) / len(scores)    # average of normalized scores at sample level
            else:
                structure_only_result[group_name] = 'NaN'
                print(f'Warning: Empyty matched samples for {group_name}.')

        return samples, {'TEDS': result, 'TEDS_structure_only': structure_only_result}


@METRIC_REGISTRY.register("Edit_dist")
class call_Edit_dist():
    def __init__(self, samples):
        self.samples = samples
    def evaluate(self, group_info=[], save_name='default'):
        samples = self.samples
        for sample in samples:
            img_name = sample['img_id'] if sample['img_id'].endswith('.jpg') or sample['img_id'].endswith('.png') else '_'.join(sample['img_id'].split('_')[:-1])
            sample['image_name'] = img_name
            gt = sample['norm_gt'] if sample.get('norm_gt') else sample['gt']
            pred = sample['norm_pred'] if sample.get('norm_pred') else sample['pred']
            upper_len = max(len(pred), len(gt))
            sample['upper_len'] = upper_len
            if len(pred) > 0 or len(gt) > 0:
                edit_dist = Levenshtein.distance(pred, gt)
                if not sample.get('metric'):
                    sample['metric'] = {}
                sample['metric']['Edit_dist'] = edit_dist / upper_len
                sample['Edit_num'] = edit_dist

        if isinstance(samples, list):
            saved_samples = samples
        else:
            saved_samples = samples.samples
        
        if not saved_samples:
            return samples, {'Edit_dist': {'ALL_page_avg': 'NaN'}}

        df = pd.DataFrame(saved_samples)
        up_total_avg = df.groupby("image_name").apply(lambda x: x['Edit_num'].sum() / x['upper_len'].sum()) # page level, sum of edits divided by sum of max(gt,pred) lengths for each sample
        all_total_avg = df['Edit_num'].sum() / df['upper_len'].sum()
        # all_total_avg = df["Edit_dist"].mean()
        per_img_score = up_total_avg.to_dict()
        with open(result_path(f'{save_name}_per_page_edit.json'), 'w', encoding='utf-8') as f:
            json.dump(per_img_score, f, indent=4, ensure_ascii=False)        
        
        # if 'display_formula' in save_name:
        #     return samples, {'Edit_dist': {'ALL_page_avg': all_total_avg}}
        # else:
        #     return samples, {'Edit_dist': {'ALL_page_avg': up_total_avg.mean()}}
        
        edit_whole = df['Edit_num'].sum() / df['upper_len'].sum()
        df['ratio'] = df['Edit_num'] / df['upper_len']
        edit_sample_avg = df['ratio'].mean()
        # edit_sample_avg = df['metric']['Edit_dist'].mean()
        return samples, {'Edit_dist': {'ALL_page_avg': up_total_avg.mean(), 'edit_whole': edit_whole, 'edit_sample_avg': edit_sample_avg}}

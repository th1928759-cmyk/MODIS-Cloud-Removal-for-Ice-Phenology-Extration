def extract_phenology_dates(df, stability_days=30):
    """提取物候日期：FUS, FUE, BUS, BUE (采用不可逆判定逻辑)"""
    df = df.sort_values('date').reset_index(drop=True)
    n = len(df)
    phenology = {'FUS': None, 'FUE': None, 'BUS': None, 'BUE': None}
    
    def check_future(idx, condition_func):
        check_range = min(stability_days, n - 1 - idx)
        if check_range < 1: return False
        future_data = df.loc[idx+1 : idx+check_range, 'moving_avg']
        return all(condition_func(val) for val in future_data)

    # 1. 查找 FUS (>=10)
    for i in range(n - 1):
        if df.loc[i, 'moving_avg'] >= 10:
            if check_future(i, lambda x: x >= 10):
                phenology['FUS'] = df.loc[i, 'date']
                break 
    
    # 2. 查找 FUE (>=90)
    start_idx = df[df['date'] == phenology['FUS']].index[0] if phenology['FUS'] is not None else 0
    for i in range(start_idx, n - 1):
        if df.loc[i, 'moving_avg'] >= 90:
            if check_future(i, lambda x: x >= 90):
                phenology['FUE'] = df.loc[i, 'date']
                break

    # 3. 查找 BUS (<=90)
    start_idx = df[df['date'] == phenology['FUE']].index[0] if phenology['FUE'] is not None else int(n/2)
    for i in range(start_idx, n - 1):
        if df.loc[i, 'moving_avg'] <= 90:
            if check_future(i, lambda x: x <= 90):
                phenology['BUS'] = df.loc[i, 'date']
                break

    # 4. 查找 BUE (<=10)
    start_idx = df[df['date'] == phenology['BUS']].index[0] if phenology['BUS'] is not None else start_idx
    for i in range(start_idx, n - 1):
        if df.loc[i, 'moving_avg'] <= 10:
            if check_future(i, lambda x: x <= 10):
                phenology['BUE'] = df.loc[i, 'date']
                break
                
    return phenology

def calculate_durations(phenology):
    """计算 ICD, CFD, FUD, BUD 时长"""
    durations = {'ICD': None, 'CFD': None, 'FUD': None, 'BUD': None}
    
    if phenology['FUS'] and phenology['BUE']: durations['ICD'] = (phenology['BUE'] - phenology['FUS']).days + 1
    if phenology['FUE'] and phenology['BUS']: durations['CFD'] = (phenology['BUS'] - phenology['FUE']).days + 1
    if phenology['FUS'] and phenology['FUE']: durations['FUD'] = (phenology['FUE'] - phenology['FUS']).days + 1
    if phenology['BUS'] and phenology['BUE']: durations['BUD'] = (phenology['BUE'] - phenology['BUS']).days + 1
        
    return durations

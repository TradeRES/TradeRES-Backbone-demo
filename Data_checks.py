# Python version used: 3.10.12
import pandas as pd

# NOTE: from the filters on each side of Data_checks_exporter,
# choose one from the other and the equivalent one from the other to avoid inputs being from another scenario than the results.

################  Loading the data from the input and results excel files

print('Loading result data...')

result_sheets   = ['transfer', 'genUnit', 'capacity', 'unit_invest', 'nodeState']
results         = pd.read_excel('BB_results_exported@Data_checks_exporter.xlsx', sheet_name=result_sheets)

# get the scenario name (only works for base-europe5 and the vre+/-flex+/- scenarios)
if results['genUnit']['scen'].values[0].startswith('base'):
    scen_name = 'base-europe5'
else:
    # e.g. "vre+flex-europe5"
    scen_name = results['genUnit']['scen'].values[0][0:16]

print('Loading input data...')

input_sheets    = ['transmission_capacities', 'storage_capacities', 'unit_node_parameters', 'ts_cf', 'flow_unit']
inputs          = pd.read_excel('BB_Spine_DB_direct_exported@Data_checks_exporter.xlsx', sheet_name=input_sheets)
# these tests assume that the wind-cf-variation alternative is not used NOT ANYMORE
#inputs['ts_cf']         = pd.read_excel('TradeRES_base_data_powersystem.xlsx', sheet_name='ts_cf')
#flow_unit_links = pd.read_excel('TradeRES_base_data_powersystem.xlsx', sheet_name='flowUnit')
print(f'\nRunning tests for scenario {scen_name}.\n')

# renaming columns for convenience
results['capacity'].columns     = ['grid', 'node', 'unit', 'existing_capacity']
results['unit_invest'].columns  = ['unit', 'invested_capacity']

# messages for passed and failed tests
test_passed, test_failed = ['Test passed.\n', 'Test failed!\n']
# will be set to false if a test fails
all_tests_passed = True
#  will include dataframes of failed test results that will be written to failed_tests.xlsx
failed_tests = {}

# values over 100 mean that a capacity limit is violated (but some slack, app. 0.01 - 0.1 percent, is necessary)
gen_cap_percent_limit       = 100.01
state_percent_limit         = 100.01
trans_cap_percent_limit     = 100.01
cf_percent_limit            = 100.1

# if the problematic_data dataframe (created as input for the following tests) is empty, the test will pass.
# Otherwise it will be added to failed_tests.
def test(problematic_data:pd.DataFrame, sheet_name:str):
    global all_tests_passed
    if len(problematic_data) > 0:
        print(test_failed)
        all_tests_passed = False
        failed_tests[sheet_name] = problematic_data
    else:
        print(test_passed)


################## Preliminary data manipulation

# creating dummy columns for grid and node to be edited later (the unit_invest sheet does not contain either)
results['unit_invest']['grid'] = 'dummy_grid'
results['unit_invest']['node'] = 'dummy_node'
# just reordering the columns for convenience
results['unit_invest'] = results['unit_invest'][['grid', 'node', 'unit', 'invested_capacity']]

# add grid and node names to invested units (required for checking storage capacities)
for row in results['unit_invest'].itertuples():
    if 'H2' in row.unit in row.unit or 'electrolyser' in row.unit:
        results['unit_invest'].iloc[row.Index,0] = 'H2'
        results['unit_invest'].iloc[row.Index,1] = f'{row.unit[:2]} H2'
    elif 'Batteries New' in row.unit:
        results['unit_invest'].iloc[row.Index,0] = 'battery'
        results['unit_invest'].iloc[row.Index,1] = f'{row.unit[:2]} battery new'
    else:
        results['unit_invest'].iloc[row.Index,0] = 'elec'
        results['unit_invest'].iloc[row.Index,1] = f'{row.unit[:2]} elec'


# H2 turbines in the BB_results_exported@input_result_exporter.xlsx "capacity" sheet are initially linked with the "elec" grid
# It, however, receives only 0.4 of the total H2 used.
# The grids and nodes are changed to H2 and country_code H2, respectively.
for row in results['capacity'].itertuples():
    if 'turbine' in row.unit:
        results['capacity'].iloc[row.Index,0] = 'H2'
        results['capacity'].iloc[row.Index,1] = f'{row.unit[:2]} H2'

# merge the existing and invested capacities and turn NaN-values to 0
capacities_all = results['capacity'].query('existing_capacity > 0.000001').merge(
    results['unit_invest'], how='outer', on=['grid', 'node', 'unit']).fillna(0)
# create tot_capacity column (the sum of existing and invested capacity)
capacities_all = capacities_all.assign(
    tot_capacity=lambda x: x.existing_capacity + x.invested_capacity)

# get timestep columns in the genUnit sheet
gen_timestep_cols = results['genUnit'].columns.drop(['grid', 'node', 'unit', 'scen'])
# add column including sum of annual production
results['genUnit']['gen_sum'] = results['genUnit'][gen_timestep_cols].sum(axis=1)
# replace NaN values with 0 and remove rows for which annual production is practically zero
results['genUnit'] = results['genUnit'].fillna(0).query('abs(gen_sum) > 0.00001')


############# TEST: units with generation also have a capacity limit

units_with_cap = capacities_all.drop_duplicates(subset=['grid', 'node', 'unit'])
units_with_gen = results['genUnit'].drop_duplicates(subset=['grid', 'node', 'unit'])

# units with gen that do not have cap (this is bad)
units_with_gen_no_cap = units_with_gen[~units_with_gen['unit'].isin(units_with_cap['unit'])]

print('Testing that all units with generation also have a capacity limit.')
test(units_with_gen_no_cap, 'genUnit_no_capacity')


############# TEST: energy from country-specific nodes and units only flows within the same country.

# fuel nodes are not country-specific so they are removed from the next test
fuel_nodes = ['Gas', 'H2', 'Hard Coal', 'Lignite', 'Nuclear', 'Oil', 'biofuel', 'waste', 'Synthetic methane']
# a filter for finding the node-unit pairs with differing countries
differing_countries = results['genUnit']['node'].str[0:2] != results['genUnit']['unit'].str[0:2]
units_with_cross_country_gens = results['genUnit'].query('node not in @fuel_nodes').loc[differing_countries]

print("Testing that energy from country-specific nodes and units only flows within the same country.")
test(units_with_cross_country_gens, 'genUnit_mixed_countries')


############# TEST: genUnit capacities are not violated

# merge capacities_all with genUnit and put (melt) all timesteps in one column
gen_with_cap = results['genUnit'].merge(capacities_all, how='left', on=['grid', 'node', 'unit']).melt(
    id_vars=['grid', 'node', 'unit', 'scen', 'tot_capacity', 'gen_sum', 'existing_capacity', 'invested_capacity'],
    var_name='timestep',
    value_name='gen')

# add column with percentage of gen capacity used (gen_tot_cap_percent)
gen_with_cap = gen_with_cap.assign(gen_tot_cap_percent=lambda x: x.gen/x.tot_capacity*100)

# create dataframe with the hours during which capacity limits are violated (this should be empty)
genUnit_cap_violations = gen_with_cap.query('gen_tot_cap_percent > @gen_cap_percent_limit')
genUnit_cap_violations = genUnit_cap_violations[['grid', 'node', 'unit', 'scen', 'existing_capacity', 'invested_capacity',
                                                 'tot_capacity', 'timestep', 'gen', 'gen_tot_cap_percent']]

print('Testing that all genUnit values do not exceed their capacity upper limits.')
test(genUnit_cap_violations, 'genUnit_cap_violations')


############# TEST: generation stays below limits determined by the capacity factors

# move timesteps of inputs['ts_cf'] (from TradeRES_base_data_powersystem.xlsx) to one column FIX THIS
inputs['ts_cf'] = inputs['ts_cf'].drop('f', axis=1)
#.melt(
#    id_vars=['flow', 'node', 'alternative', 'forecast index'],
#    var_name='timestep',
#    value_name='cf')

# create 'country' columns to both inputs['ts_cf'] and inputs['flow_unit'] to help with merging capacity factors with corresponding units
inputs['ts_cf'] = inputs['ts_cf'].assign(country=lambda x: x.node.str[0:2])
inputs['flow_unit'] = inputs['flow_unit'].assign(country=lambda x: x.unit.str[0:2])

# do the merge
cf_with_units = inputs['ts_cf'].merge(inputs['flow_unit'], how='left', on=['flow', 'country'])[['node', 'unit', 'timestep', 'cf']]

# merge the capacity factors with generation data
cf_with_gen_and_cap = gen_with_cap.merge(cf_with_units.query(
    'unit in @gen_with_cap["unit"]'), # in the input data, only check for units that have gen in the model run
    how='left', on=['node', 'unit', 'timestep']).query('cf.notna()') # remove rows without capacity factors

# create column for how far the gen is from the upper limit determined by capacity factors (in %)
cf_with_gen_and_cap = cf_with_gen_and_cap.assign(gen_cf_percent=lambda x: (x.gen/(x.tot_capacity*x.cf))*100)

# create dataframe for hours that violate capacity factors (this should, again, be empty)
cf_violations = cf_with_gen_and_cap.query('gen_cf_percent > @cf_percent_limit').drop('gen_sum', axis=1)
cf_violations = cf_violations[['grid', 'node', 'unit', 'scen', 'existing_capacity', 'invested_capacity',
                               'tot_capacity', 'timestep', 'gen', 'gen_tot_cap_percent', 'cf', 'gen_cf_percent']]
print('Testing that genUnit values do not exceed the limits set by capacity factors.')
test(cf_violations, 'cf_violations')


############### TEST: node states stay within storage capacity limits

# get upper limit capacity ratios for h2 and batteries
h2_upper_limit_capacity_ratio = inputs['unit_node_parameters'].query(
    'upperLimitCapacityRatio > 0 and grid=="H2"')['upperLimitCapacityRatio'].values[0]
bat_upper_limit_capacity_ratio = inputs['unit_node_parameters'].query(
    'upperLimitCapacityRatio > 0 and grid=="battery"')['upperLimitCapacityRatio'].values[0]

# filter results['unit_invest'] for battery and h2 storage investments
bat_storage_investments = results['unit_invest'].query('grid=="battery"').drop_duplicates(subset='invested_capacity').drop('unit', axis=1)
# add impact of upper limit capacity ratios to invested storages (and call the resulting column upwardLimit like in the input data)
bat_storage_investments['upwardLimit'] = bat_storage_investments['invested_capacity'] * bat_upper_limit_capacity_ratio
# drop the invested_capacity column (it is just the invested capacity without the upper limit capacity ratio impact)
bat_storage_investments = bat_storage_investments.drop('invested_capacity', axis=1)

# same for h2
h2_storage_investments = results['unit_invest'].query('grid=="H2" and unit.str.contains("storage")').drop('unit', axis=1)
h2_storage_investments['upwardLimit'] = h2_storage_investments['invested_capacity'] * h2_upper_limit_capacity_ratio
h2_storage_investments = h2_storage_investments.drop('invested_capacity', axis=1)

# combine invested h2 and battery capacities as well as existing capacities together
existing_storage_capacities = inputs['storage_capacities']
all_storage_capacities = pd.concat([bat_storage_investments, h2_storage_investments, existing_storage_capacities])

# add upwardLimits to results['nodeState']
states_plus_upward_limits = results['nodeState'].merge(all_storage_capacities, how='left', on=['grid', 'node']).fillna(0)

# add column including maximum realized state values over the year
timestep_cols = states_plus_upward_limits.columns.drop(['grid', 'node', 'scen', 'upwardLimit'])
states_plus_upward_limits['state_realized_max'] = states_plus_upward_limits[timestep_cols].max(axis=1)

# melt the timesteps into one column
states_plus_upward_limits = states_plus_upward_limits.melt(
                            id_vars=['grid', 'node', 'scen', 'upwardLimit', 'state_realized_max'],
                            var_name='timestep',
                            value_name='state')

# add column for state value as percentage of total storage capacity
states_plus_upward_limits = states_plus_upward_limits.assign(state_percent=lambda x: x.state/x.upwardLimit*100)

# create the dataframe for testing
state_cap_violations = states_plus_upward_limits.query(f'upwardLimit > 0 and state_percent > {state_percent_limit}')
nodeState_columns_to_excel = ['grid', 'node', 'scen', 'state_realized_max', 'upwardLimit']

# to avoid too large output size, we limit output to one row per grid-node pair
# state_cap_violations = state_cap_violations[nodeState_columns_to_excel].drop_duplicates(subset=['grid', 'node'])

# add the percentage of storage/state capacity used
state_cap_violations['state_cap_percent'] = state_cap_violations['state_realized_max']/state_cap_violations['upwardLimit'] * 100

print('Testing that state values for nodes do not exceed storage capacity limits.')
test(state_cap_violations, 'nodeState_cap_violations')


############### TEST: transmissions of energy stay within capacity limits

inputs['transmission_capacities'].columns = ['grid', 'fromNode', 'toNode', 'transferCap']

trans_with_cap = results['transfer'].merge(inputs['transmission_capacities'], how='left', on=['grid', 'fromNode', 'toNode']).melt(
    id_vars=['grid', 'fromNode', 'toNode', 'scen', 'transferCap'],
    var_name='timestep',
    value_name='gen').fillna(0)

trans_with_cap = trans_with_cap.assign(trans_cap_percent=lambda x: x.gen/x.transferCap*100)
trans_cap_violations = trans_with_cap.query('trans_cap_percent > @trans_cap_percent_limit')

print("Testing that transfers within elec nodes are within capacity limits.")
test(trans_cap_violations, 'transfer_cap_violations')


############# TEST: storage cycling (discharging and charging at the same time)




############# TEST: units with investments but no generation

# create an overview table for capacities, investments and total generation (will be always generated)

# add gen_max and gen_sum columns to capacities_all
gen_with_gen_sum_timestep_cols = results['genUnit'].columns.drop(['grid', 'node', 'unit', 'scen', 'gen_sum'])

# add column including max of annual production
results['genUnit'] = results['genUnit'].reset_index()
results['genUnit']['gen_abs_max'] = results['genUnit'][gen_timestep_cols].max(axis=1)

# replace gen_max values for negative gens

gen_sum_index = results['genUnit'].columns.get_loc("gen_sum")
gen_max_index = results['genUnit'].columns.get_loc("gen_abs_max")

for row in results['genUnit'].itertuples():
    row_gen_max = results['genUnit'].iloc[row.Index, gen_max_index]
    row_gen_sum = results['genUnit'].iloc[row.Index, gen_sum_index]
    # negative row_gen_max, while the sum of production is non-zero, implies negative production 
    if row_gen_max <= 0.01 and abs(row_gen_sum) > 0.01:
        results['genUnit'].iloc[row.Index, gen_max_index] = abs(results['genUnit'][gen_timestep_cols].iloc[[row.Index]].min(axis=1))

gen_sums_and_maxes = results['genUnit'][['grid', 'node', 'unit', 'gen_sum', 'gen_abs_max']]
capacities_all_to_excel = capacities_all.merge(gen_sums_and_maxes, how='left', on=['grid', 'node', 'unit']).assign(
    # the maximum percentage used of total capacity
    gen_abs_max_cap_percent=lambda x: x.gen_abs_max/x.tot_capacity*100).fillna(0)
# add a scenario name column
capacities_all_to_excel['scen'] = results['genUnit']['scen'].values[0]

units_with_cap_no_gen = capacities_all_to_excel.query('gen_sum.abs() < 0.01 and invested_capacity > 0')
if len(units_with_cap_no_gen) > 0:
    print('\nWARNING: there are units with invested capacity but no generation.\n')
    for row in units_with_cap_no_gen.itertuples():
        print(f'Grid: {row.grid}, node: {row.node}, unit: {row.unit}, invested capacity: {row.invested_capacity}')
    print(f'\nPlease check them in the gnu_investments_no_gen sheet of data_checks_{scen_name}.xlsx.\n')



################# Create output

if all_tests_passed:
    print('Tests done. All tests passed!')
else:
    print(f'Tests done: {len(failed_tests)} test(s) failed! See the sheet(s) failed_{list(failed_tests.keys())} in data_checks_{scen_name}.xlsx.')

print(f'Writing data_checks_{scen_name}.xlsx.')

with pd.ExcelWriter(f'data_checks_{scen_name}.xlsx') as writer:
    # create sheets for failed tests
    for failed_test_name in failed_tests.keys():
        print(f'Creating sheet {failed_test_name}...')
        failed_tests[failed_test_name].to_excel(writer, sheet_name='failed_' + failed_test_name, index=False)
    print('Creating sheet gnu_cap_gen_overview...')
    capacities_all_to_excel.to_excel(writer, sheet_name='gnu_cap_gen_overview', index=False)
    if len(units_with_cap_no_gen) > 0:
        print('Creating sheet gnu_investments_no_gen...')
        units_with_cap_no_gen.to_excel(writer, sheet_name='gnu_investments_no_gen')
    print('\nAll done.\n')

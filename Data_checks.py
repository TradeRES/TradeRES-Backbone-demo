# Python version used: 3.10.12
import pandas as pd

# NOTE: from the filters on each side of Data_checks_exporter,
# choose one from the other and the equivalent one from the other to avoid inputs being from another scenario than the results.

################  Loading the data from the input and results excel files

print('Loading result data...')

result_sheets   = ['transfer', 'genUnit', 'capacity', 'unit_invest', 'nodeState', 'nodePrice']
results         = pd.read_excel('BB_results_exported@Data_checks_exporter.xlsx', sheet_name=result_sheets)

# get the scenario name (only works for base-europe5 and the vre+/-flex+/- scenarios)
if results['genUnit']['scen'].values[0].startswith('base'):
    scen_name = 'base-europe5'
else:
    # e.g. "vre+flex-europe5"
    scen_name = results['genUnit']['scen'].values[0][0:16]

print('Loading input data...')

input_sheets    = ['transmission_capacities', 'storage_capacities', 'unit_node_parameters', 'ts_cf', 'flow_unit', 'fuel_prices']
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

# values over 100 mean that a capacity limit is violated (but some slack, app. 0.1 percent, is necessary)
gen_cap_percent_limit       = 100.10
state_percent_limit         = 100.10
trans_cap_percent_limit     = 100.10
cf_percent_limit            = 100.10

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

# remove epsilon-sized investments
results['unit_invest'] = results['unit_invest'].query('invested_capacity > 0.001').reset_index()

# creating dummy columns for grid and node to be edited later (the unit_invest sheet does not contain either)
results['unit_invest']['grid'] = 'dummy_grid'
results['unit_invest']['node'] = 'dummy_node'
# just reordering the columns for convenience
results['unit_invest'] = results['unit_invest'][['grid', 'node', 'unit', 'invested_capacity']]

# add grid and node names to invested units (required for checking storage capacities)
for row in results['unit_invest'].itertuples():
    if 'H2' in row.unit in row.unit or 'electrolyser' in row.unit:
        results['unit_invest'].iloc[row.Index,0] = 'H2'                 # grid name
        results['unit_invest'].iloc[row.Index,1] = f'{row.unit[:2]} H2' # node name
    elif 'Batteries New' in row.unit:
        results['unit_invest'].iloc[row.Index,0] = 'battery'
        results['unit_invest'].iloc[row.Index,1] = f'{row.unit[:2]} battery new'
    elif 'Hydro' in row.unit:
        results['unit_invest'].iloc[row.Index,0] = 'hydro'
        results['unit_invest'].iloc[row.Index,1] = f'{row.unit[:2]} hydro'
    elif 'PHS' in row.unit:
        results['unit_invest'].iloc[row.Index,0] = 'pumped'
        results['unit_invest'].iloc[row.Index,1] = f'{row.unit[:2]} ps'
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
fuel_nodes = inputs['fuel_prices']['fuel']

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
genUnit_cap_violations = genUnit_cap_violations[['grid', 'node', 'unit', 'existing_capacity', 'invested_capacity',
                                                 'tot_capacity', 'timestep', 'gen', 'gen_tot_cap_percent', 'scen']]

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

results['unit_invest'] = results['unit_invest'].query('invested_capacity > 0.001')
upper_limit_capacity_ratios = inputs['unit_node_parameters'][['unit', 'upperLimitCapacityRatio']].query('upperLimitCapacityRatio.notna()')
storage_investments = results['unit_invest'].merge(upper_limit_capacity_ratios, how='right').query('invested_capacity.notna()')
storage_investments['invested_storage_cap'] = storage_investments['invested_capacity'] * storage_investments['upperLimitCapacityRatio']
storage_investments = storage_investments.drop(['invested_capacity', 'upperLimitCapacityRatio', 'unit'], axis=1)

existing_storage_capacities = inputs['storage_capacities'].query('upwardLimit > 0.001')
existing_storage_capacities = existing_storage_capacities.rename(columns={'upwardLimit':'existing_storage_cap'})
all_storage_capacities = existing_storage_capacities.merge(storage_investments, on=['grid', 'node'], how='outer').fillna(0)
all_storage_capacities = all_storage_capacities.assign(tot_storage_cap = lambda x: x.existing_storage_cap + x.invested_storage_cap)

# add storage capacity data to results['nodeState']
states_plus_upward_limits = results['nodeState'].merge(all_storage_capacities, how='outer', on=['grid', 'node']).fillna(0)

# melt the timesteps into one column
states_plus_upward_limits = states_plus_upward_limits.melt(
                            id_vars=['grid', 'node', 'scen', 'existing_storage_cap', 'invested_storage_cap', 'tot_storage_cap'],
                            var_name='timestep',
                            value_name='state')

# add column for state value as percentage of total storage capacity
states_plus_upward_limits = states_plus_upward_limits.assign(state_percent=lambda x: x.state/x.tot_storage_cap*100)

# create the dataframe for testing
state_cap_violations = states_plus_upward_limits.query(f'tot_storage_cap > 0 and state_percent > {state_percent_limit}')

state_cap_violations = state_cap_violations[['grid', 'node', 'scen', 'timestep', 'state', 'existing_storage_cap', 'invested_storage_cap', 'tot_storage_cap', 'state_percent']]

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
    # negative row_gen_max, while the sum of production is non-zero, implies negative production which is turned positive
    if row_gen_max <= 0.01 and abs(row_gen_sum) > 0.01:
        results['genUnit'].iloc[row.Index, gen_max_index] = abs(results['genUnit'][gen_timestep_cols].iloc[[row.Index]].min(axis=1))

gen_sums_and_maxes = results['genUnit'][['grid', 'node', 'unit', 'gen_sum', 'gen_abs_max']]
capacities_all_to_excel = capacities_all.merge(gen_sums_and_maxes, how='left', on=['grid', 'node', 'unit']).assign(
    # the maximum percentage used of total capacity
    gen_abs_max_cap_percent=lambda x: x.gen_abs_max/x.tot_capacity*100).fillna(0)
# add a scenario name column
capacities_all_to_excel['scen'] = results['genUnit']['scen'].values[0]



########### Warnings

# Warns if there are units with invested capacity but no generation (excluding H2 storage units for which generation is not expected)
units_with_cap_no_gen = capacities_all_to_excel.query('gen_sum.abs() < 0.01 and invested_capacity > 0')
units_with_cap_no_gen = units_with_cap_no_gen[['grid', 'node', 'unit', 'existing_capacity',
                                               'invested_capacity', 'tot_capacity', 'gen_sum', 'scen']]

if len(units_with_cap_no_gen.query('~unit.str.contains("H2 storage")')) > 0: # len(units_with_cap_no_gen) > 0 and 
    print('\nWARNING: there are units with invested capacity but no generation.\n')
    for row in units_with_cap_no_gen.itertuples():
        if 'H2 storage' not in row.unit:
            print(f'Grid: {row.grid}, node: {row.node}, unit: {row.unit}, invested capacity: {row.invested_capacity}')
    print(f'\nSee the gnu_investments_no_gen sheet in data_checks_{scen_name}.xlsx.\n')

# Warns if there are over 20 hours of 4000 EUR/MWh prices for any elec node in nodePrice
node_prices = results['nodePrice'].copy()
node_prices.columns = node_prices.iloc[0]
elec_prices = node_prices.drop(0).filter(like='elec').reset_index(drop=True)
dummy_hour_limit = 20

elec_dummy_df = pd.DataFrame(columns=['node', 'dummy_hour_qty'])
for node in elec_prices.columns:
    dummy_hour_qty = len(elec_prices[1:][node].loc[lambda x : x < -3999])
    if dummy_hour_qty > dummy_hour_limit:
        elec_dummy_df.loc[len(elec_dummy_df.index)] = [node, dummy_hour_qty]

if len(elec_dummy_df) > 0:
    print(f'WARNING: marginal electricity costs reach 4000 EUR/MWh (dummy generation) for over {dummy_hour_limit} hours in the following nodes:\n')
    for row in elec_dummy_df.itertuples():
        print(f'Node {row.node}, {row.dummy_hour_qty} hours.')

# modify elec_prices for an overview Excel sheet
elec_price_overview = elec_prices.copy().transpose().rename(columns={0:'scen'}).reset_index().rename(columns={0:'node'})
# get only hourly price columns and turn the electricity prices positive
price_timestep_columns = elec_price_overview.copy()[elec_price_overview.columns.drop(['node', 'scen'])].abs()
elec_price_overview[price_timestep_columns.columns] = price_timestep_columns
elec_price_overview = elec_price_overview.copy() # to avoid fragmentation of dataframe

elec_price_overview['min'] = price_timestep_columns.min(axis=1)
elec_price_overview['quartile_1'] = price_timestep_columns.quantile(0.25, axis=1)
elec_price_overview['median'] = price_timestep_columns.quantile(0.50, axis=1)
elec_price_overview['quartile_3'] = price_timestep_columns.quantile(0.75, axis=1)
elec_price_overview['max'] = price_timestep_columns.max(axis=1)
elec_price_overview['avg'] = price_timestep_columns.sum(axis=1)/8760.0
# add the quantities of hours with dummy gen
elec_price_overview = elec_price_overview.merge(elec_dummy_df, how='outer')
elec_price_overview['dummy_hour_qty'] = elec_price_overview['dummy_hour_qty'].fillna(0)


# exclude the hourly prices
elec_price_overview = elec_price_overview[['node', 'scen', 'price_min', 'price_max', 'quartile_1', 'median', 'quartile_3', 'price_avg', 'dummy_hour_qty']]

################# Create output

if all_tests_passed:
    print('\nTests done. All tests passed!\n')
else:
    print(f'Tests done: {len(failed_tests)} test(s) failed! See the sheet(s) failed_{list(failed_tests.keys())} in data_checks_{scen_name}.xlsx.\n')

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
        units_with_cap_no_gen.to_excel(writer, sheet_name='gnu_investments_no_gen', index=False)
    print('Creating sheet elec_price_overview...')
    elec_price_overview.to_excel(writer, sheet_name='elec_price_overview', index=False)
    print('\nAll done.\n')

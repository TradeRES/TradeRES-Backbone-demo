$ontext
This file is part of Backbone.

Backbone is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Backbone is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with Backbone.  If not, see <http://www.gnu.org/licenses/>.
$offtext

* =============================================================================
* --- Model Definition - Schedule ---------------------------------------------
* =============================================================================

if (mType('schedule'),
    m('schedule') = yes; // Definition, that the model exists by its name

* --- Define Key Execution Parameters in Time Indeces -------------------------

    // Define simulation start and end time indeces
    mSettings('schedule', 't_start') = 1;  // First time step to be solved, 1 corresponds to t000001 (t000000 will then be used for initial status of dynamic variables)
    mSettings('schedule', 't_end') = 48; // Last time step to be included in the solve (may solve and output more time steps in case t_jump does not match)
*    mSettings('schedule', 't_end') = 8760; // Last time step to be included in the solve (may solve and output more time steps in case t_jump does not match)

    // Define simulation horizon and moving horizon optimization "speed"
    mSettings('schedule', 't_horizon') = 8*24;    // How many active time steps the solve contains (aggregation of time steps does not impact this, unless the aggregation does not match)
    mSettings('schedule', 't_jump') = 12;          // How many time steps the model rolls forward between each solve

    // Define length of data for proper circulation
    mSettings('schedule', 'dataLength') = 8760;

* =============================================================================
* --- Model Time Structure ----------------------------------------------------
* =============================================================================

* --- Define Samples ----------------------------------------------------------

    // Number of samples used by the model
    mSettings('schedule', 'samples') = 1;

    // Define Initial and Central samples
    ms_initial('schedule', 's000') = yes;
    ms_central('schedule', 's000') = yes;

    // Define time span of samples
    msStart('schedule', 's000') = 1;
    msEnd('schedule', 's000') = msStart('schedule', 's000') + mSettings('schedule', 't_horizon');

    // Define the probability (weight) of samples
    p_msAnnuityWeight('schedule', 's000') = 1;
    p_msProbability('schedule', s) = 0;
    p_msProbability('schedule', 's000') = 1;
    p_msWeight('schedule', s) = 0;
    p_msWeight('schedule', 's000') = 8760 / mSettings('schedule', 't_end');

* --- Define Time Step Intervals ----------------------------------------------

    // Define the duration of a single time-step in hours
    mSettings('schedule', 'stepLengthInHours') = 24;

    // Define the time step intervals in time-steps
    mInterval('schedule', 'stepsPerInterval', 'c000') = 1;
    mInterval('schedule', 'lastStepInIntervalBlock', 'c000') = 1*24;
    mInterval('schedule', 'stepsPerInterval', 'c001') = 3;
    mInterval('schedule', 'lastStepInIntervalBlock', 'c001') = 2*24;
    mInterval('schedule', 'stepsPerInterval', 'c002') = 6;
    mInterval('schedule', 'lastStepInIntervalBlock', 'c002') = mSettings('schedule', 't_horizon');

* =============================================================================
* --- Model Forecast Structure ------------------------------------------------
* =============================================================================

    // Define the number of forecasts used by the model
    mSettings('schedule', 'forecasts') = 0;

    // Define Realized and Central forecasts
    mf_realization('schedule', 'f00') = yes;
    mf_central('schedule', 'f00') = yes;

    // Define forecast probabilities (weights)
    p_mfProbability('schedule', f) = 0;
    p_mfProbability(mf_realization('schedule', f)) = 1;


* =============================================================================
* --- Model Features ----------------------------------------------------------
* =============================================================================

* --- Define Reserve Properties -----------------------------------------------

    // Define whether reserves are used in the model
    mSettingsReservesInUse('schedule', 'primary', 'up') = yes;
    mSettingsReservesInUse('schedule', 'primary', 'down') = no;
    mSettingsReservesInUse('schedule', 'secondary', 'up') = no;
    mSettingsReservesInUse('schedule', 'secondary', 'down') = no;
    mSettingsReservesInUse('schedule', 'tertiary', 'up') = yes;
    mSettingsReservesInUse('schedule', 'tertiary', 'down') = no;
    mSettingsReservesInUse('schedule', 'ffr2', 'up') = yes;
    mSettingsReservesInUse('schedule', 'ffr2', 'down') = no;
    mSettingsReservesInUse('schedule', 'ffr3', 'up') = no;
    mSettingsReservesInUse('schedule', 'ffr3', 'down') = no;

* --- Define Unit Approximations ----------------------------------------------

    // Define the last time step for each unit aggregation and efficiency level (3a_periodicInit.gms ensures that there is a effLevel until t_horizon)
    mSettingsEff('schedule', 'level1') = 24;
    mSettingsEff('schedule', 'level3') = 48;
    mSettingsEff('schedule', 'level2') = Inf;

* --- Control the solver ------------------------------------------------------

    // Control the use of advanced basis
    mSettings('schedule', 'loadPoint') = 0;  // 0 = no basis, 1 = latest solve, 2 = all solves, 3 = first solve
    mSettings('schedule', 'savePoint') = 0;  // 0 = no basis, 1 = latest solve, 2 = all solves, 3 = first solve

); // END if(mType)

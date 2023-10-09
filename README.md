# TradeRES Backbone demo

This is a Spine Toolbox 'project' that uses the Backbone energy system optimization tool.

## Prerequisites

1. These instructions guide you to install the demo using git, so make sure you have git: [https://git-scm.com/download/win](https://git-scm.com/download/win). 
2. Backbone is built in [GAMS](https://www.gams.com/download/), which is a commercial modelling language. You need to first install GAMS and make sure you have a working licence for it.
3. Next, install Spine Toolbox using the [Spine Toolbox installation guide](https://github.com/spine-tools/Spine-Toolbox#installation). 

## Installation

1.	Open Command Prompt.
2.	Change the current working directory to the location where you want to have the TradeRES Backbone demo repository.
3.	Type `git clone https://github.com/TradeRES/TradeRES-Backbone-demo.git` and press enter.

    ```
    git clone https://github.com/TradeRES/TradeRES-Backbone-demo.git
    ```

4.	Change the current working directory to the newly added TradeRES-Backbone-demo directory.
5.	Type `git submodule init` and press enter.

    ```
    git submodule init
    ```

6.	Type `git submodule update` and press enter.

    ```
    git submodule update
    ```

## Upgrading

Spine Toolbox and this project are constantly evolving. To get the latest versions, do the following:

1.	Upgrade Spine Toolbox (see [instructions](https://github.com/spine-tools/Spine-Toolbox#installation)):
2.	Upgrade this project by changing your current working directory to the TradeRES-Backbone-demo directory and running `git pull`.

    ```
    git pull
    ```

## Configuring and running the workflow

1.	First, launch Spine Toolbox (see [instructions](https://github.com/spine-tools/Spine-Toolbox#installation)).
2.	Make sure Spine Toolbox knows where the local GAMS executable is (File -> Settings -> Tools). You may also want to limit the number of concurrent processes (File -> Settings -> Engine -> Maximum number of concurrent processes -> User defined limit: 2, for example).
3.	Then, open this project from Spine Toolbox (File -> Open project...). The workflow is run from right to left. The inputs are on the right-hand side and the data store for the outputs is on the left-hand side. 
4.	Configure the input Data Store **BB_Spine_DB_direct**: Select its icon in the *Design View* and in the *Data Store Properties*, select Dialect: sqlite. Choose a folder and name for the database or use the default. Then, click *New Spine db*.
5.	Import database and scenario templates to the input Data Store: Open the **BB_Spine_DB_direct** Data Store in the DB Editor by double-clicking its icon (or by selecting its icon and clicking *Open editor...*). In the DB Editor, import the **database_template.json** file stored in the *Data* folder (Menu -> Import...). Import also the **scenario_template.json** file from the same *Data* folder (Menu -> Import...). Commit changes (Menu -> Commit...) and close the DB Editor.
6.	Import data into the input Data Store: In the *Design View*, select the **BB_Excel_to_SpineDB** Importer icon. In the top bar of Spine Toolbox, click the *Selection* button next to *Execute*. To make sure that the data has been imported, double-click the **BB_Spine_DB_direct** Data Store icon and check that the DB Editor can show objects and parameter values.
7.	Optional step to create another scenario where fossil units have been disabled: 
    1.	Select the **BB_input_Excel** Data Connection icon. In the *Data Connection Properties*, click the plus icon next to *File paths*. Go to the *Data* folder, copy-paste *empty_data.xlsx* to the same folder and rename the new file to *alternative_data.xlsx*. Back in the *Data Connection Properties*, double-click the *alternative_data.xlsx* file path to open the Excel file. Go to the *p_unit* worksheet. Copy the data below and paste it to cell A1. After pasting, make sure cell A1 contains text *unit* (delete an empty row from the beginning if needed). Save and close the *alternative_data.xlsx* file.

    |unit|alternative|eff00|availability|investMIP|maxUnitCount|is_active|eff01|op00|op01|minUnitCount|unitCount|
    |:----|:----|:----|:----|:----|:----|:----|:----|:----|:----|:----|:----|
    |DE Gas|nofossil| | | | |no| | | | | |
    |DE Hard Coal|nofossil| | | | |no| | | | | |
    |DE Lignite|nofossil| | | | |no| | | | | |
    |DE Oil|nofossil| | | | |no| | | | | |
    |DE Others non-renewable|nofossil| | | | |no| | | | | |

    2.	Run the **BB_Excel_to_SpineDB** Importer as in step 6. (To make importing faster, you can choose to re-import only the new file: Click the **BB_Excel_to_SpineDB** Importer icon in the *Design View*, go to *Importer Properties* and, under *Available resources*, select only the *alternative_data.xlsx* file. Then, in the top bar of Spine Toolbox, click the *Selection* button next to *Execute*. After running the Importer, you may want to select again the original file under *Available resources* for future data imports.)
    3.	Double-click the **BB_Spine_DB_direct** Data Store icon. In the DB Editor, go to the *Scenario tree*, select *Type new scenario name here...* and write `base-germany-nofossil`. Select the arrow next to the newly added scenario name, select *Type scenario alternative name here...* and write `base`. Select *Type scenario alternative name here...* again and write `base-germany`. Finally, select *Type scenario alternative name here...* again and write `nofossil`. You can use keyboard arrows to move in the *Scenario tree*. Commit changes (Menu -> Commit...) and close the DB Editor.
    4. Save the project (File -> Save project).
8.	Filter the scenarios you want to run: In the *Design View*, click the filter/funnel icon between **BB_Spine_DB_direct** and **BB_sets**. Make sure you have selected Backbone under *Tool filter* and the scenarios you want to run under *Scenario filter*. Save the project (File -> Save project).
9.	Export data from the input Data Store to the Backbone tool: Select the **Export_to_BB** Exporter icon in the *Design View*. In the top bar of Spine Toolbox, click the *Selection* button next to *Execute*.
10.	Optional step to test the Backbone tool instead of running the full model: Select the **BB_input_files** Data Connection in the *Design View*. 
    1.	Double-click file path ending with *investInit.gms* to open the file in a text editor. Go to line 42 where the number of samples is given and replace 7 by 1. This will change the number of representative weeks in the investment optimization phase from 7 to 1. Save and close the file.
    2.	Double-click file path ending with *scheduleInit.gms* to open the file in a text editor. Go to line 29 where t_end parameter is given and replace 8760 by 168. This will change the operational phase of the run from one year run to one week. Save and close the file.
11.	Configure and run the Backbone tool with investment and operational phases: Select the **Backbone_loop** Tool icon in the *Design View*. In the top bar of Spine Toolbox, click the *Selection* button next to *Execute*. 
    a.	If GAMS is not found, open the specification editor by double-clicking the **Backbone_loop** Tool icon. Go to line 12, add `::` to the beginning of the line and remove `..` from the beginning of line 13. Set your correct GAMS path on line 13. Repeat on lines 35-36. Save the specification file and close the specification editor. Try running again by clicking the *Selection* button next to *Execute*.
    b.	If GAMS is still not found, open the specification editor again. Go to line 13, add `::` to the beginning of the line and remove `::` from the beginning of line 14. Modify the command on line 14 according to what you would normally use when running GAMS from command line. Repeat on lines 36-37. Save the specification file. Try running again by clicking the *Selection* button next to *Execute*.
12.	Configure the output Data Store: Select the **BB_results** Data Store icon in the *Design View*. In the *Data Store Properties*, select Dialect: sqlite. Choose a folder and name for the database or use the default. Then, click *New Spine db*.
13.	Import results to the output Data Store: Select the **BB_result_invest** and **Result_import** Importer icons in the *Design View*. In the top bar of Spine Toolbox, click the *Selection* button next to *Execute*.
14.	In the *Design View*, double-click the **BB_results** Data Store icon to view the results.

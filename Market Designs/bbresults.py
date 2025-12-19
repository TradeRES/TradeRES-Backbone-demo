
from cgi import test
from functools import partial
from tkinter import W
from turtle import filling
import numpy as np
from gams import GamsWorkspace
import pandas as pd
import os
from pathlib import Path
import re
import subprocess as sp
from io import StringIO
from matplotlib.pyplot import get_cmap
from matplotlib.colors import to_hex
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from brokenaxes import brokenaxes
#import geopandas as gpd
#import contextily as ctx

class BackboneResult:
    def __init__(self, path):
        ws = GamsWorkspace(system_directory='C:/GAMS/49')
        if not os.path.isabs(path):
            # TODO: if path.lower() contains " äöü" this won't work
            path = os.path.join(os.getcwd(), path)

        self._path = path
        self.gams_db = ws.add_database_from_gdx(path)
        self.mMettings = self.gams_db.get_parameter("mSettings")

        # invest or schedule
        self.model_type = self.mMettings.first_record().keys[0]
        self.stepLengthInHours = self.mMettings.find_record(
            keys=[self.model_type, "stepLengthInHours"]
        ).value
        
        # allows easy access of results
        self.set_results_as_attribs()

        if not self.r_qGen().empty:
            print("WARNING: Model has dummy generation.")

    def set_results_as_attribs(self):
        for symbol in self._result_symbols:
            setattr(self, symbol, partial(self.param_as_df_gdxdump,symbol))

    color_dict={'Solar CSP':'lemonchiffon','Solar PV large':'gold', 'Solar CSP New':'lemonchiffon','Solar PV large New':'yellow',
             'Solar PV rooftop New':'yellow','Batteries Discharge New': 'cyan', 'Batteries Charge New': 'cyan',  'Wind Onshore New':'lightgrey',
             'ROR':'lightblue', 'Run of River':'lightblue','Wind Onshore New 1':'darkgrey', 'Wind Onshore New 2':'darkgrey', 
             'Wind Onshore': 'lightgrey', 'Wind Offshore New':'dimgrey',
             'Wind Onshore High FLH':'darkgrey', 'Wind Onshore High MV':'lightgrey',
             'Solar PV rooftop':'yellow','Batteries Discharge New': 'cyan', 'Batteries Charge New': 'cyan',
             'Hydro Discharge':'mediumblue', 'PHS Charge':'deepskyblue', 'PHS Discharge':'deepskyblue', 'Pumped Hydro Storage':'deepskyblue', 
             'Pumped Hydro Discharge':'deepskyblue', 'HVAC_elec':'hotpink', 'electric HVAC':'hotpink','HVAC_fuel':'darkmagenta','ev':'violet',
             'Batteries New Discharge': 'cyan', 'Batteries New Charge': 'cyan', 'ror': 'dodgerblue',
             'Batteries Discharge': 'cyan', 'Batteries Charge': 'cyan', 'ROR': 'dodgerblue', 'supplier':'hotpink',
             'Batteries Res Discharge': 'darkcyan', 'electric HVAC':'hotpink', 'fuel HVAC':'darkmagenta',
             'Batteries Res Charge': 'darkcyan', 'aggregator': 'orange','EV':'orange',
             'Wind Offshore':'dimgrey', 'electrolyser': 'darkcyan','H2 electrolyser': 'darkcyan','Other non-thermal renewables':'lightblue',
             'Others renewable':'darkgreen', 'Thermal renewables':'darkseagreen','Waste':'darkgreen','Other thermal renewables':'darkgreen','Nuclear':'purple', 'Nuclear New':'purple',
             'Others non-renewable':'peachpuff', 'Others renewable New':'darkgreen', 'Oil':'orange', 'Biofuel New':'limegreen',
             'Gas':'peru', 'Synthetic Gas':'peru', 'Biofuel':'limegreen', 'Hard Coal':'black', 'Lignite':'saddlebrown',  'H2 turbine': 'turquoise', 'H2 Turbine': 'turquoise',
             'residential.A2WHP_DHW': 'green', 'residential.A2WHP_radiators': 'green', 'residential.ideal_cooling': 'green',
             'ev': 'orange', 'Load':'blue','DSR':'red','dsr':'red','biofuel':'limegreen','Demand-Side Response':'red'}
    pass    

    #adapted backbone_path   
    @property
    def _backbone_path(self):
        """path to the backbone repository
        """
        return Path(__file__).parent.parent.joinpath("C:/Users/silke/WORK/3_Model/TradeRES-Backbone-demo/TradeRES-Backbone-demo/Backbone/")

    @property
    def _result_symbols(self):
        """list of possible symbols in the {result_file}.gdx as defined in backbone\defOutput\resultSymbols.inc
        """
        result_symbole_file = self._backbone_path.joinpath("defOutput/resultSymbols_2x.inc")
        with result_symbole_file.open("r") as symbol_file:
            text = symbol_file.read()
            symbols = re.findall(r"^[rt]_[a-zA-Z]*", text, re.MULTILINE)
        return symbols
    
    def set_as_df(self, set_name):
        gms_set = self.gams_db.get_set(set_name)
        data = [[*rec.keys] for rec in gms_set]
        domains = [x if type(x) == str else x.name for x in gms_set.domains]

        set_df = pd.DataFrame(data=data,columns=domains)
        return set_df

    def param_as_df(self, param_name, convert_time=True):
        gms_param = self.gams_db.get_parameter(param_name)
        data = [[*rec.keys, rec.value] for rec in gms_param]

        # domains have changed and now may contain sets
        domains = [x if type(x) == str else x.name for x in gms_param.domains]

        columns = domains + ["value"]
        param_df = pd.DataFrame(data=data, columns=columns)

        if convert_time:
            if "t" in param_df.columns:
                param_df["t"] = param_df["t"].apply(lambda t: int(t[1:]))

        return param_df

    def param_as_df_gdxdump(self, param_name, encoding="1252", convert_time=True):
        """ Use the 'gdxdump' GAMS utility via subprocess to convert a parameter into a pd.DataFrame.
        This is sometimes beneficial, to circumvent decoding errors
        """
        gdxdump = sp.run(["gdxdump", self._path, "format", "csv", "symb", param_name],stdout=sp.PIPE)
        csv_data = gdxdump.stdout.decode(encoding=encoding)
        header = csv_data.partition("\n")[0]


        header = [x.strip("\"") for x in header.split(",")]
        dtypes = [str if x != "Val" else float for x in header]
        dtypes = dict(zip(header,dtypes))
        df = pd.read_csv(StringIO(csv_data),dtype=dtypes, na_values="Eps")

        if convert_time:
            if "t" in df.columns:
                df["t"] = df["t"].apply(lambda t: int(t[1:]))

        return df

    def eqn_as_df(self, eqn_name):
        gms_eqn = self.gams_db.get_equation(eqn_name)

        data = [[*rec.keys, rec.level, rec.marginal, rec.lower, rec.upper, rec.scale] for rec in gms_eqn]
        columns = [x if type(x) == str else x.name for x in gms_eqn.domains] + ['level', 'marginal', 'lower', 'upper', 'scale']

        eqn_df = pd.DataFrame(data=data, columns=columns)
        return eqn_df



class BackboneScenarioAnalysis:
    def __init__(self, results_dir=None, result_files=None) -> None:
        if results_dir and not result_files:
            abs_dir = Path(results_dir).resolve()
            unsorted_results = list(abs_dir.glob(r"*.gdx"))
            self.result_files = sorted(unsorted_results)
        elif not results_dir and result_files:
            self.result_files = result_files
        else:
            raise ValueError(
                "Only one of the parameters 'results_dir' or 'result_files' must be passed"
            )
    
        self.bb_results = [
            BackboneResult(path.as_posix()) for path in self.result_files
        ]

        # scenario names will be derived from the filenames
        self.scenarios = [x.stem.replace("_", " ") for x in self.result_files]
               
        # define colors as sequence:
        self.colors = self._get_n_hex_colors_from_cmap(
            "Spectral_r", len(self.result_files)
        )

        # define colors as sequence for the number of scenarios: 
        self.colors_scen = self._get_n_hex_colors_from_cmap(
            "Spectral_r", len(self.scenarios)
        )

        #colors for my units
        self.color_dict={'Solar CSP':'lemonchiffon','Solar PV large':'gold', 'Solar CSP New':'lemonchiffon','Solar PV large New':'yellow',
            'Solar PV rooftop New':'gold','Batteries Discharge New': 'cyan', 'Batteries Charge New': 'cyan', 'Wind Onshore New':'lightgrey',  'Wind Offshore New':'dimgrey',
             'ROR':'lightblue', 'Run of River':'lightblue','Wind Onshore New 1':'darkgrey', 'Wind Onshore New 2':'lightgrey', 
               'Wind Onshore': 'grey', 'Exogenous Wind Onshore': 'grey', 'Wind Offshore':'dimgrey',
                'Wind Onshore High FLH':'darkgrey', 'Wind Onshore High MV':'lightgrey',
             'Solar PV rooftop':'yellow','Batteries Discharge New': 'cyan', 'Batteries Charge New': 'cyan',
             'Hydro Discharge':'mediumblue', 'PHS Charge':'deepskyblue', 'PHS Discharge':'deepskyblue', 'Pumped Hydro Storage':'deepskyblue',
             'Pumped Hydro Discharge':'deepskyblue', 'HVAC_elec':'hotpink', 'HVAC_fuel':'darkmagenta','electric HVAC':'hotpink','fuel HVAC':'darkmagenta',
             'Batteries New Discharge': 'cyan', 'Batteries New Charge': 'cyan', 'ror': 'dodgerblue',
             'Batteries Discharge': 'cyan', 'Batteries Charge': 'cyan', 'Batteries Res Discharge': 'darkcyan','supplier':'hotpink',
              'Batteries Res Charge': 'darkcyan', 'ROR': 'dodgerblue',  'H2 plant': 'darkcyan', 'aggregator': 'lemonchiffon', 'H2 CCGT': 'darkcyan',
              'electrolyser': 'darkcyan','H2 electrolyser': 'darkcyan','Synthetic Gas':'peru','EV':'orange','Other non-thermal renewables':'lightblue',
             'Other thermal renewables': 'darkgreen','Thermal renewables':'darkseagreen','Waste': 'darkgreen',
             'Others renewable':'darkgreen', 'Nuclear':'purple', 'Nuclear New':'purple',
             'Others non-renewable':'peachpuff', 'Others renewable New':'darkgreen', 'Oil':'orange', 'Biofuel New':'limegreen',
             'Gas':'peru', 'Biofuel':'limegreen', 'Hard Coal':'black', 'Lignite':'saddlebrown',  'H2 turbine': 'turquoise', 'H2 Turbine': 'turquoise',
             'residential.A2WHP_DHW': 'green', 'residential.A2WHP_radiators': 'green', 'residential.ideal_cooling': 'green',
             'ev': 'orange', 'EV':'orange','Load':'blue','DSR':'red','dsr':'red','Demand-Side Response':'red','biofuel':'limegreen', 'H2 storage': 'blue'}
        pass
    
    @property
    def set_as_df(self, set_name):
        gms_set = self.gams_db.get_set(set_name)
        data = [[*rec.keys] for rec in gms_set]
        domains = [x if type(x) == str else x.name for x in gms_set.domains]
        set_df = pd.DataFrame(data=data,columns=domains)
        return set_df

    @staticmethod
    def _get_n_hex_colors_from_cmap(cmap_name, n):
        cmap = get_cmap(cmap_name)
        fracs = np.linspace(0, 1, n)
        return [to_hex(cmap(f)) for f in fracs]

    #Prices       
    #Plot Price Duration Curves with all scenarios per node
    def plot_priceDurationCurve_scens(self, nodes=[],font="Open Sans",grid='elec',stylelist=[],colorlist=[],ymin=0,ymax=500,yd=50):   
        result=self.bb_results[0]
        r_balanceMarginal=result.r_balanceMarginal()    
        if not nodes:
            nodes=r_balanceMarginal[r_balanceMarginal['grid']==grid]['node'].drop_duplicates()
        ax_list = []
        df=pd.DataFrame()
        if not colorlist:
            colorlist=self._get_n_hex_colors_from_cmap("viridis",len(self.scenarios))
        if not stylelist:
            stylelist = []
            for x in range(len(self.scenarios)):
                for element in  ['-', '--', '-.', ':']:
                    stylelist.append(element)
        for s, r in zip(self.scenarios, self.bb_results): 
            r_balanceMarginal=r.r_balanceMarginal() 
            r_balanceMarginal=r_balanceMarginal[r_balanceMarginal["node"].apply(lambda x: 1 if any(i in x for i in ["elec"]) else 0)==1]
            r_balanceMarginal["scenario"]=str(s)
            r_balanceMarginal["Val"]=r_balanceMarginal["Val"].fillna(0)
            p_gnu_io=r.param_as_df("p_gnu_io")
            p_gnu_io["vomCosts"]=p_gnu_io[p_gnu_io['param_gnu']=='vomCosts']["value"]
            p_gnu_io=p_gnu_io.groupby(['node','grid','unit']).sum().reset_index()
            unitUnittype=r.set_as_df("unitUnittype")
            p_gnu_io=p_gnu_io.merge(unitUnittype,on="unit")
            dsr=p_gnu_io[p_gnu_io["unittype"]=="dsr"]
            dsr=dsr[["node","vomCosts"]]
            dsr=dsr.rename(columns={"vomCosts": "maxprice"})
            r_balanceMarginal=r_balanceMarginal.merge(dsr,on=["node"])
            r_balanceMarginal["Val"][r_balanceMarginal["Val"]<r_balanceMarginal["maxprice"]*-1]=r_balanceMarginal["maxprice"]*-1
            #r_balanceMarginal["Val"]=r_balanceMarginal["Val"].fillna(0)
            #r_balanceMarginal["Val"][r_balanceMarginal["Val"]<-200]=-200
            r_balanceMarginal["node"]=r_balanceMarginal["node"].map(lambda x: str(x)[:2])
            df=pd.concat([df,r_balanceMarginal])
        for n in nodes:
            df_plot=df[df['node']==n]
            df_plot = df_plot.pivot(columns=["scenario"],index="t", values="Val")
            df_plot = pd.DataFrame(np.sort(df_plot.values, axis=0)*-1, index=df_plot.index, columns=df_plot.columns)
            ax=df_plot.plot.line(title=str(n)[:2],style=stylelist,lw=1,color=colorlist,fontsize=14)
            ax.set_title(str(n)[:2], fontsize=14)
            ax.set_xticks([])
            #remove this is if you customize axis
            #ax.set_yticks(range(min(0,int(min(df_plot.values))),int(max(df_plot.values)),
            #    round((int(max(df_plot.values))-min(0,int(min(df_plot.values))))/20)),fontname=font)
            #uncomment these to manually adapt yaxis range and ticks
            #ax.set_yticks(range(ymin,ymax,yd))
            ax.set_yticklabels(range(ymin,ymax,yd), fontname=font,fontsize=14)
            ax.set_yticks(range(ymin, ymax, yd))
            ax.set_ylim(ymin, ymax)
            ax.set_xlim(0, 8760)
            #ax.spines['top'].set_visible(False)
            #ax.spines['right'].set_visible(False)
            ax.set_xlabel('Hours (sorted)',fontname=font,fontsize=14)
            ax.set_ylabel('€/MWh',fontname=font,fontsize=14)
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
            #ax.axis('off')
            ax.spines[['right', 'top','bottom']].set_visible(False)
            ax.legend()
            ax.legend(loc='center left', bbox_to_anchor=(1, 0.5),prop={'family':font,'size': 14},frameon=False)
            ax_list.append(ax)
            #name="C:\ws\TradeRES\TradeRES-Backbone-demo\.spinetoolbox\items/backbone_loop\output/230209_MDu/graphs/PriceDurationCurve"+str(n)+".png"
            #plt.savefig(name, dpi=300, bbox_inches='tight')
        
        return ax_list

    #one plot per scenario/node
    def plot_priceDurationCurve_scens3(self, nodes=[],font=[],grid='elec',stylelist=[],colorlist=[],ymax=200,yd=50,ymin=0):   
        result=self.bb_results[0]
        r_balanceMarginal=result.r_balanceMarginal()    
        if not nodes:
            nodes=r_balanceMarginal[r_balanceMarginal['grid']==grid]['node'].drop_duplicates()
        nodes=sorted(nodes)
        ax_list = []
        nodelist=[]
        df=pd.DataFrame()

        if not colorlist:
            colorlist=self._get_n_hex_colors_from_cmap("viridis",len(self.scenarios))
        if not stylelist:
            stylelist = []
            for x in range(len(self.scenarios)):
                for element in  ['-', '--', '-.', ':']:
                    stylelist.append(element)
        for s, r in zip(self.scenarios, self.bb_results): 
            r_balanceMarginal=r.r_balanceMarginal() 
            r_balanceMarginal=r_balanceMarginal[r_balanceMarginal["node"].apply(lambda x: 1 if any(i in x for i in ["elec"]) else 0)==1]
            r_balanceMarginal["scenario"]=str(s)
            r_balanceMarginal["Val"]=r_balanceMarginal["Val"].fillna(0)
            p_gnu_io=r.param_as_df("p_gnu_io")
            p_gnu_io["vomCosts"]=p_gnu_io[p_gnu_io['param_gnu']=='vomCosts']["value"]
            p_gnu_io=p_gnu_io[p_gnu_io['input_output']=='output']
            p_gnu_io=p_gnu_io.groupby(['node','grid','unit']).sum().reset_index()
            unitUnittype=r.set_as_df("unitUnittype")
            p_gnu_io=p_gnu_io.merge(unitUnittype,on="unit")
            dsr=p_gnu_io[p_gnu_io["unittype"]=="dsr"]
            dsr=dsr[["node","vomCosts"]]
            dsr=dsr.rename(columns={"vomCosts": "maxprice"})
            r_balanceMarginal=r_balanceMarginal.merge(dsr,on=["node"])
            r_balanceMarginal["Val"][r_balanceMarginal["Val"]<r_balanceMarginal["maxprice"]*-1]=r_balanceMarginal["maxprice"]*-1
            df=pd.concat([df,r_balanceMarginal])
        for n in nodes:
            df_plot=df[df['node']==n]
            df_plot = df_plot.pivot(columns=["scenario"],index="t", values="Val")
            df_plot = pd.DataFrame(np.sort(df_plot.values, axis=0)*-1, index=df_plot.index, columns=df_plot.columns)
            nodelist.append(str(n[:2]))
            ax_list.append(df_plot)
        nrow=4
        ncol=5
        fig, axes = plt.subplots(nrow, ncol, sharex=True)
        count=0
        for r in range(nrow):
            for c in range(ncol):
                if ((r==nrow-1) and (c==ncol-1)):                    
                    axes[r,c].axis('off')
                else:
                    ax_list[count].plot(ax=axes[r,c],style=stylelist,lw=1,color=colorlist)
                    axes[r,c].set_title(nodelist[count])
                    count+=1
                    axes[r,c].spines['top'].set_visible(False)
                    axes[r,c].spines['right'].set_visible(False)    
                    axes[r,c].get_legend().remove()  
                    axes[r,c].set_xticks([])
                    axes[r,c].set_yticks([])
                    axes[r,c].set_xlabel("")
                    axes[r,c].axhline(y=0, color='black', linestyle='-', linewidth=1)

        for r in range(nrow):
            axes[r,1].set_ylabel('€/MWh',fontname=font)
            axes[r,1].set_ylim(ymin, ymax)
            axes[r,1].set_yticks(range(ymin,ymax,yd))
            axes[r,1].set_xlim(0, 8760)
        for c in range(ncol):
            axes[3,c].set_xlabel('Hours (sorted)',fontname=font)
        axes[3,3].legend(loc='center left', bbox_to_anchor=(1, 0.5),prop={'family':font},frameon=False)
        fig.set_figwidth(15)
        fig.set_figheight(8)



    def plot_priceDurationCurve_scens2(self, nodes=[],font=[],grid='elec',stylelist=[],colorlist=[],ymax=200,yd=50,ymin=0):   
        result=self.bb_results[0]
        r_balanceMarginal=result.r_balanceMarginal()    
        if not nodes:
            nodes=r_balanceMarginal[r_balanceMarginal['grid']==grid]['node'].drop_duplicates()
        nodes=sorted(nodes)
        ax_list = []
        nodelist=[]
        df=pd.DataFrame()

        if not colorlist:
            colorlist=self._get_n_hex_colors_from_cmap("viridis",len(self.scenarios))
        if not stylelist:
            stylelist = []
            for x in range(len(self.scenarios)):
                for element in  ['-', '--', '-.', ':']:
                    stylelist.append(element)
        for s, r in zip(self.scenarios, self.bb_results): 
            r_balanceMarginal=r.r_balanceMarginal() 
            r_balanceMarginal=r_balanceMarginal[r_balanceMarginal["node"].apply(lambda x: 1 if any(i in x for i in ["elec"]) else 0)==1]
            r_balanceMarginal["scenario"]=str(s)
            r_balanceMarginal["Val"]=r_balanceMarginal["Val"].fillna(0)
            p_gnu_io=r.param_as_df("p_gnu_io")
            p_gnu_io["vomCosts"]=p_gnu_io[p_gnu_io['param_gnu']=='vomCosts']["value"]
            p_gnu_io=p_gnu_io[p_gnu_io['input_output']=='output']
            p_gnu_io=p_gnu_io.groupby(['node','grid','unit']).sum().reset_index()
            unitUnittype=r.set_as_df("unitUnittype")
            p_gnu_io=p_gnu_io.merge(unitUnittype,on="unit")
            dsr=p_gnu_io[p_gnu_io["unittype"]=="dsr"]
            dsr=dsr[["node","vomCosts"]]
            dsr=dsr.rename(columns={"vomCosts": "maxprice"})
            r_balanceMarginal=r_balanceMarginal.merge(dsr,on=["node"])
            r_balanceMarginal["Val"][r_balanceMarginal["Val"]<r_balanceMarginal["maxprice"]*-1]=r_balanceMarginal["maxprice"]*-1
            df=pd.concat([df,r_balanceMarginal])
        for n in nodes:
            df_plot=df[df['node']==n]
            df_plot = df_plot.pivot(columns=["scenario"],index="t", values="Val")
            df_plot = pd.DataFrame(np.sort(df_plot.values, axis=0)*-1, index=df_plot.index, columns=df_plot.columns)
            nodelist.append(str(n[:2]))
            ax_list.append(df_plot)
        nrow=4
        ncol=5
        fig, axes = plt.subplots(nrow, ncol)
        count=0
        for r in range(nrow):
            for c in range(ncol):
                if ((r==nrow-1) and (c==ncol-1)):                    
                    axes[r,c].axis('off')
                else:
                    ax_list[count].plot(ax=axes[r,c],style=stylelist,lw=1,color=colorlist)
                    axes[r,c].set_title(nodelist[count])
                    count+=1
                    axes[r,c].spines['top'].set_visible(False)
                    axes[r,c].spines['right'].set_visible(False)    
                    axes[r,c].get_legend().remove()  
                    axes[r,c].set_xticks([])
                    axes[r,c].set_xlabel("")
                    axes[r,c].set_yticks([])
                    axes[r,c].set_ylabel("")
                    axes[r,c].spines['bottom'].set_visible(False)
                    axes[r,c].set_ylim(ymin, ymax)
                    axes[r,c].set_yticks(range(ymin,ymax,yd))
                    axes[r,c].axhline(y=0, color='black', linestyle='-', linewidth=1)
        for r in range(nrow):
            axes[r,0].set_ylabel('€/MWh',fontname=font)
            axes[r,0].set_ylim(ymin, ymax)
            axes[r,0].set_yticks(range(ymin,ymax,yd))
            axes[r,0].set_xlim(0, 8760)
        for r in range(nrow):
            axes[r,2].set_yticklabels([])
            axes[r,3].set_yticklabels([])
            axes[r,4].set_yticklabels([])
            axes[r,1].set_yticklabels([])
        for c in range(ncol):
            axes[3,c].set_xlabel('Hours (sorted)',fontname=font)
        axes[3,3].legend(loc='center left', bbox_to_anchor=(1, 0.5),prop={'family':font},frameon=False)
        fig.set_figwidth(15)
        fig.set_figheight(8)

    #Plot Price Duration Curves with all nodes per scenario
    def plot_priceDurationCurve_nodes(self, nodes=[],font="Open Sans",grid='elec',stylelist=[],colorlist=[],ymin=0,ymax=500,yd=50):   
        result=self.bb_results[0]
        r_balanceMarginal=result.r_balanceMarginal()
        r_balanceMarginal=r_balanceMarginal[r_balanceMarginal['grid']==grid]
        ax_list = []
        if not stylelist:
            stylelist = []
            for x in range(len(self.bb_results[0].r_balanceMarginal().node)):
                for element in  ['-', '--', '-.', ':']:
                    stylelist.append(element)
        if not colorlist:
            colorlist=self._get_n_hex_colors_from_cmap("viridis",len(r_balanceMarginal.node.drop_duplicates().transpose().tolist()))
        for s, r in zip(self.scenarios, self.bb_results): 
            r_balanceMarginal=r.r_balanceMarginal() 
            r_balanceMarginal=r_balanceMarginal[r_balanceMarginal['grid']==grid]
            p_gnu_io=r.param_as_df("p_gnu_io")
            p_gnu_io["vomCosts"]=p_gnu_io[p_gnu_io['param_gnu']=='vomCosts']["value"]
            p_gnu_io=p_gnu_io.groupby(['node','grid','unit']).sum().reset_index()
            unitUnittype=r.set_as_df("unitUnittype")
            p_gnu_io=p_gnu_io.merge(unitUnittype,on="unit")
            dsr=p_gnu_io[p_gnu_io["unittype"]=="dsr"]
            dsr=dsr[["node","vomCosts"]]
            dsr=dsr.rename(columns={"vomCosts": "maxprice"})
            r_balanceMarginal=r_balanceMarginal.merge(dsr,on=["node"])
            r_balanceMarginal["Val"][r_balanceMarginal["Val"]<r_balanceMarginal["maxprice"]*-1]=r_balanceMarginal["maxprice"]*-1
            #r_balanceMarginal["Val"]=r_balanceMarginal["Val"].fillna(0)
            #r_balanceMarginal["Val"][r_balanceMarginal["Val"]<-200]=-200
            r_balanceMarginal["node"]=r_balanceMarginal["node"].map(lambda x: str(x)[:2])
            df_plot = r_balanceMarginal.pivot(columns="node",index="t", values="Val")
            df_plot = pd.DataFrame(np.sort(df_plot.values, axis=0)*-1, index=df_plot.index, columns=df_plot.columns)
            ax=df_plot.plot.line(title=str(s),style=stylelist,lw=1,color=colorlist)
           # ax.set_xticks([])
           # ax.set_yticks(range(min(0,int(df_plot.values.min())),int(df_plot.values.max()),
           #     round((int(df_plot.values.max())-min(0,int(df_plot.values.min())))/20)),fontname=font)
            #uncomment these to manually adapt yaxis range and ticks
            ax.set_yticks(range(ymin,ymax,yd))
            ax.set_yticklabels(range(ymin,ymax,yd), fontname=font)
            ax.set_ylim(ymin, ymax)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.set_xlabel('Hours (sorted)',fontname=font)
            ax.set_ylabel('Price (€/MWh)',fontname=font)
            ax.legend()
            ax.legend(loc='center left', bbox_to_anchor=(1, 0.5),prop={'family':font},frameon=False)
            ax_list.append(ax)
            #name="C:\ws\TradeRES\TradeRES-Backbone-demo\.spinetoolbox\items/backbone_loop\output/230209_MDu/graphs/PriceDurationCurve"+str(n)+".png"
            #plt.savefig(name, dpi=300, bbox_inches='tight')
        return ax_list


    #Generation 
    #Generation share by type over scenario (not distinguished by nodes)
    def plot_genShare(self,grid='elec',category=[],w=500,unitlist=[]):
        df_final=pd.DataFrame()
       # input=res_invest.bb_results[1].set_as_df("unitUnittype")
        colors=pd.DataFrame(self.color_dict.items(), columns=['unittype', 'color'])
        for s, r, in zip(self.scenarios, self.bb_results):
            r_gTotalConsumption=r.r_gTotalConsumption().rename(columns={"Val": "cons"})
            #r_gTotalConsumption[r_gTotalConsumption["grid"]=="H2"]["grid"]="elec"
            #df2=r_gTotalConsumption[r_gTotalConsumption['grid'].apply(lambda x: 1 if any(i in x for i in ["elec","pros"]) else 0)==1]
            df2=r_gTotalConsumption[r_gTotalConsumption.grid == grid]

            r_genGridUnittypeTotal= r.param_as_df("r_genGridUnittypeTotal").rename(columns={"value": "gen"})
            df=r_genGridUnittypeTotal[r_genGridUnittypeTotal.grid == grid]
            #df=r_gnuTotalGen_unittype[r_gnuTotalGen_unittype["grid"]==grid]
            #df=pd.merge(df,input,on="unit")
            #drop battery charge units
            #list=["Charge","electrolyser"]
            if grid == "pros":
                df2["cons"]=df2["cons"].apply(lambda x: x-df[df.unittype=="aggregator"]["gen"].values[0])
                df.loc[df["unittype"]=="Solar PV rooftop","gen"]=df[df.unittype=="Solar PV rooftop"]["gen"].apply(lambda x: x+df[df.unittype=="aggregator"]["gen"].values[0])
            #else:
            #    continue

            #df[df.grid=="pros"]["gen"].apply(lambda x: abs(x))
            df=pd.merge(df,colors,on="unittype")
            df=df[df["gen"]>0]
            print(df)
            
            #rename stuff
            df["type"]=df["unittype"]
 
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 plant"]) else 0)==1]="H2 CCGT"
            #df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 electrolyser"]) else 0)==1]="Electrolyser"
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 turbine"]) else 0)==1]="H2Turbine"
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["Batteries"]) else 0)==1]="Batteries"
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["PHS"]) else 0)==1]="Pumped Hydro Storage"
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr"]) else 0)==1]="Demand-Side Response"
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel"]) else 0)==1]="Biofuel"
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ror"]) else 0)==1]="Run of River"
            df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["aggregator"]) else 0)==1]="Prosumer Feed-In"
            #sort stuff
            df["cat"]="b"
            df["cat"][df["type"].apply(lambda x: 1 if any(i in x for i in category) else 0)==1]="a"
            #df=df.groupby(["grid","type","color","cat"])["gen"].sum().reset_index()
            #df=df.groupby(["grid"])["gen"].sum().reset_index()
            #df=df.rename(columns={"gen": "totalgen"})
           # df["cons"]=df2["cons"]
            df["genshare"]=df["gen"].apply(lambda x: x/df2["cons"]*-1)
            df["scenario"]=str(s)
            df_final=pd.concat([df,df_final])
            df_final=df_final.sort_values(["cat","scenario"])

        fig = go.Figure()

        for u in df_final.type.unique():
            plot_df = df_final[df_final.type == u]
            fig.add_trace(
            go.Bar(x=plot_df.scenario, y=plot_df.genshare*100, name=u, width=1,marker_color=plot_df.color
            ))

        fig.update_layout(barmode='relative',plot_bgcolor='rgba(0,0,0,0)',autosize=False,
            width=w,
            height=500, font_family="Open Sans", font_color="black",yaxis_range=[0,100],
            legend=dict(
            y=0.5
            ))
        fig.update_yaxes(linecolor="black",dtick=10,title="%",title_standoff = 0.5,ticks="outside")
        fig.update_xaxes(linecolor="black")
        return fig


    def plot_totalgen(self,grid='elec',category=[],w=500,h=500,unitlist=[]):
        df_final=pd.DataFrame()
        colors=pd.DataFrame(self.color_dict.items(), columns=['unittype', 'color'])
        for s, r, in zip(self.scenarios, self.bb_results):

            r_genGridUnittypeTotal= r.param_as_df("r_genGridUnittypeTotal").rename(columns={"value": "gen"})
            df=r_genGridUnittypeTotal[r_genGridUnittypeTotal.grid == grid]
            
            #for prosumer grid
            if grid == "pros":
            #   df2["cons"]=df2["cons"].apply(lambda x: x-df[df.unittype=="aggregator"]["gen"].values[0])
                df.loc[df["unittype"]=="Solar PV rooftop","gen"]=df[df.unittype=="Solar PV rooftop"]["gen"].apply(lambda x: x+df[df.unittype=="aggregator"]["gen"].values[0])
            #else:
            #    continue

            #df[df.grid=="pros"]["gen"].apply(lambda x: abs(x))
            df=pd.merge(df,colors,on="unittype")
            #df=df[df["gen"]>0]


            #rename stuff
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 plant"]) else 0)==1]="H2 CCGT"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 electrolyser"]) else 0)==1]="Electrolyser"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 turbine"]) else 0)==1]="H2 Turbine"
           # df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["Batteries"]) else 0)==1]="Batteries"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr"]) else 0)==1]="Demand-Side Response"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel"]) else 0)==1]="Biofuel"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ror"]) else 0)==1]="ROR"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["aggregator"]) else 0)==1]="Prosumer Feed-In"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["PHS"]) else 0)==1]="Pumped Hydro Storage"

            #sort stuff
            df["cat"]="b"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category) else 0)==1]="a"
            df["scenario"]=str(s)
            df_final=pd.concat([df,df_final])
            df_final=df_final.sort_values(["unittype","scenario"])

        fig = go.Figure()

        #choose unittypes
        if not unitlist:
            unitlist=df_final.unittype.unique()
        df_final=df_final[df_final["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

        for u in df_final.unittype.unique():
            plot_df = df_final[df_final.unittype == u]
            fig.add_trace(
            go.Bar(x=plot_df.scenario, y=plot_df.gen/1000000, name=u, width=1,marker_color=plot_df.color
            ))

        fig.update_layout(barmode='relative',plot_bgcolor='rgba(0,0,0,0)',autosize=False,
            width=w,height=h,
            font_family="Open Sans", font_color="black",
            legend=dict(
            y=0.5
            ))
        fig.update_yaxes(linecolor="black",title="TWh",title_standoff = 0.5,ticks="outside")
        fig.update_xaxes(linecolor="black")
        return fig


    def plot_totalgen_bb3(self,grid='elec',category=[],w=500,h=500,unitlist=[],image=[]):
        df_final=pd.DataFrame()
        colors=pd.DataFrame(self.color_dict.items(), columns=['unittype', 'color'])
        for s, r, in zip(self.scenarios, self.bb_results):

            r_genByUnittype_gn = r.param_as_df("r_genByUnittype_gn").rename(columns={"value": "gen"})
            df=r_genByUnittype_gn[r_genByUnittype_gn.grid == grid]

            #if grid == "pros":
            #    df2["cons"]=df2["cons"].apply(lambda x: x-df[df.unittype=="aggregator"]["gen"].values[0])
            #    df.loc[df["unittype"]=="Solar PV rooftop","gen"]=df[df.unittype=="Solar PV rooftop"]["gen"].apply(lambda x: x+df[df.unittype=="aggregator"]["gen"].values[0])
            #else:
            #    continue

            #df[df.grid=="pros"]["gen"].apply(lambda x: abs(x))
            #df=df[df["gen"]>0]
            
            #rename stuff
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 plant"]) else 0)==1]="H2 CCGT"
           # df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 electrolyser"]) else 0)==1]="Electrolyser"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 turbine"]) else 0)==1]="H2 Turbine"
            #df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["Batteries"]) else 0)==1]="Batteries"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr"]) else 0)==1]="Demand-Side Response"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel"]) else 0)==1]="Biofuel"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ror"]) else 0)==1]="ROR"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["aggregator"]) else 0)==1]="Prosumer Feed-In"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["PHS"]) else 0)==1]="Pumped Hydro Storage"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ev"]) else 0)==1]="EV"
            df=df.groupby(["unittype"])["gen"].sum().reset_index()
            df=pd.merge(df,colors,on="unittype")

            #sort stuff
            df["cat"]="c"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category) else 0)==1]="a"

            #df=df[df["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

            df["scenario"]=str(s)
            df_final=pd.concat([df,df_final])
            df_final=df_final.sort_values(["unittype","scenario"])

        fig = go.Figure()

        #choose unittypes
        if not unitlist:
            unitlist=df_final.unittype.unique()
        df_final=df_final[df_final["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

        for u in df_final.unittype.unique():
            plot_df = df_final[df_final.unittype == u]
            fig.add_trace(
            go.Bar(x=plot_df.scenario, y=plot_df.gen/1000000, name=u, width=1,marker_color=plot_df.color
            ))

        fig.update_layout(barmode='relative',plot_bgcolor='rgba(0,0,0,0)',autosize=False,
            width=w,height=h,
            font_family="Open Sans", font_color="black",
            legend=dict(
            y=0.5,traceorder="reversed"
            ))
        fig.update_yaxes(linecolor="black",title="TWh",title_standoff = 0.5,ticks="outside")
        fig.update_xaxes(linecolor="black")
        fig.add_hline(y=0,line_width=0.5)
        if not image:
            pass
        else:
            fig.write_image(image,scale=5,height=h,width=w)
        return fig

    def plot_totalgen_bb3_2(self,grid='elec',category=[],category2=[],category3=[],w=500,h=500,unitlist=[],image=[],angle=90):
        df_final=pd.DataFrame()
        colors=pd.DataFrame(self.color_dict.items(), columns=['unittype', 'color'])
        for s, r, in zip(self.scenarios, self.bb_results):
            r_gen_gnu = r.param_as_df("r_gen_gnu").rename(columns={"value": "gen"})
            unitUnittype=r.set_as_df("unitUnittype")
            r_gen_gnu=r_gen_gnu.merge(unitUnittype,on="unit")
            df=r_gen_gnu[r_gen_gnu.grid == grid]
            
           # r_genByUnittype_gn = r.param_as_df("r_genByUnittype_gn").rename(columns={"value": "gen"})
           # df=r_genByUnittype_gn[r_genByUnittype_gn.grid == grid]
           # df=df.groupby(["unittype"])["gen"].sum().reset_index()

            #if grid == "pros":
            #    df2["cons"]=df2["cons"].apply(lambda x: x-df[df.unittype=="aggregator"]["gen"].values[0])
            #    df.loc[df["unittype"]=="Solar PV rooftop","gen"]=df[df.unittype=="Solar PV rooftop"]["gen"].apply(lambda x: x+df[df.unittype=="aggregator"]["gen"].values[0])
            #else:
            #    continue

            #df[df.grid=="pros"]["gen"].apply(lambda x: abs(x))
            #df=df[df["gen"]>0]
            #rename stuff
            #df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 plant"]) else 0)==1]="H2 CCGT"
            #df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 turbine"]) else 0)==1]="H2 Turbine"
            df["unittype"][df["unit"].apply(lambda x: 1 if any(i in x for i in ["Wind Onshore New 1"]) else 0)==1]="Wind Onshore High FLH"
            df["unittype"][df["unit"].apply(lambda x: 1 if any(i in x for i in ["Wind Onshore New 2"]) else 0)==1]="Wind Onshore High MV"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel","Others","Nuclear","H2 turbine"]) else 0)==1]="Thermal renewables"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr","CSP","ror","PHS","Hydro"]) else 0)==1]="Other non-thermal renewables"

            #df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["Batteries"]) else 0)==1]="Batteries"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr"]) else 0)==1]="Demand-Side Response"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel"]) else 0)==1]="Biofuel"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ror"]) else 0)==1]="ROR"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["aggregator"]) else 0)==1]="Prosumer Feed-In"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["PHS"]) else 0)==1]="Pumped Hydro Storage"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ev"]) else 0)==1]="EV"
    
            df=df.groupby(["unittype","grid"])["gen"].sum().reset_index()
            df=pd.merge(df,colors,on="unittype")
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 electrolyser"]) else 0)==1]="Electrolyser"
            #sort stuff
            df["cat"]="d"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category) else 0)==1]="a"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category2) else 0)==1]="b"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category3) else 0)==1]="c"

            #df=df[df["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

            df["scenario"]=str(s)
            df_final=pd.concat([df,df_final])
            df_final=df_final.sort_values(["cat","unittype","scenario"])

        fig = go.Figure()

        #choose unittypes
        if not unitlist:
            unitlist=df_final.unittype.unique()
        df_final=df_final[df_final["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

        for u in df_final.unittype.unique():
            plot_df = df_final[df_final.unittype == u]
            fig.add_trace(
            go.Bar(x=plot_df.scenario, y=plot_df.gen/1000000, name=u, width=1,marker_color=plot_df.color,
                               text=plot_df.gen/1000000
            ))
        fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig.update_layout(barmode='relative',plot_bgcolor='rgba(0,0,0,0)',autosize=False,
            width=w,height=h,
            font_family="Open Sans", font_color="black",
            legend=dict(
            y=0.5
            ))
        fig.update_yaxes(linecolor="black",title="TWh",title_standoff = 0.5,ticks="outside")
        fig.update_xaxes(linecolor="black",tickangle = angle)
        fig.add_hline(y=0,line_width=0.5)
        if not image:
            pass
        else:
            fig.write_image(image,scale=5,height=h,width=w)
        return fig


    def plot_totalgenshare_bb3_2(self, grid='elec',font="Open Sans",category=[],category2=[],category3=[],category4=[],size=12,w=500,h=500,unitlist=[],image=[]):
        df_final=pd.DataFrame()
        colors=pd.DataFrame(self.color_dict.items(), columns=['unittype', 'color'])
        for s, r, in zip(self.scenarios, self.bb_results):
            r_gen_gnu = r.param_as_df("r_gen_gnu").rename(columns={"value": "gen"})
            unitUnittype=r.set_as_df("unitUnittype")
            r_gen_gnu=r_gen_gnu.merge(unitUnittype,on="unit")
            df=r_gen_gnu[r_gen_gnu.grid == grid]
            df["unittype"][df["unit"].apply(lambda x: 1 if any(i in x for i in ["Wind Onshore New 1"]) else 0)==1]="Wind Onshore High FLH"
            df["unittype"][df["unit"].apply(lambda x: 1 if any(i in x for i in ["Wind Onshore New 2"]) else 0)==1]="Wind Onshore High MV"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel","Others","Nuclear","H2 turbine"]) else 0)==1]="Thermal renewables"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr","CSP","ror","PHS"]) else 0)==1]="Other non-thermal renewables"
            #df["gen"][df["unittype"]=="H2 electrolyser"]=0.00000000000001
            df=df[df["gen"]>0]
            df=df.groupby(["unittype","grid"])["gen"].sum().reset_index()
            r_gTotalConsumption=r.param_as_df("r_gTotalConsumption").rename(columns={"value": "cons"})
            r_gTotalConsumption=r_gTotalConsumption[r_gTotalConsumption["grid"]==grid]
            if grid == "pros":
            #    df2["cons"]=df2["cons"].apply(lambda x: x-df[df.unittype=="aggregator"]["gen"].values[0])
                df.loc[df["unittype"]=="Solar PV rooftop","gen"]=df[df.unittype=="Solar PV rooftop"]["gen"].apply(lambda x: x+df[df.unittype=="aggregator"]["gen"].values[0])
            #else:
            #    continue

            #df[df.grid=="pros"]["gen"].apply(lambda x: abs(x))
            #sum up some stuff as "other"
            df=pd.merge(df,colors,on="unittype")
            df=pd.merge(df,r_gTotalConsumption,on="grid")
            #change wind onshore color
            #df["color"][df["unittype"]=="Wind Onshore"]="darkgrey"
            #df=df[df["gen"]>0]
            
            #rename stuff
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 plant"]) else 0)==1]="H2 CCGT"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 electrolyser"]) else 0)==1]="Electrolyser"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 turbine"]) else 0)==1]="H2 Turbine"
           # df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["Batteries"]) else 0)==1]="Batteries"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr"]) else 0)==1]="Demand-Side Response"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel"]) else 0)==1]="Biofuel"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ror"]) else 0)==1]="ROR"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["aggregator"]) else 0)==1]="Prosumer Feed-In"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["PHS"]) else 0)==1]="Pumped Hydro Storage"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ev"]) else 0)==1]="EV"

            #sort stuff
            df["cat"]="d"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category) else 0)==1]="a"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category2) else 0)==1]="b"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category3) else 0)==1]="c"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category4) else 0)==1]="e"

            #df=df[df["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]
            df["scenario"]=str(s)
            df_final=pd.concat([df,df_final])
            df_final=df_final.sort_values(["cat","unittype","scenario"])
        fig = go.Figure()

        #choose unittypes
        if not unitlist:
            unitlist=df_final.unittype.unique()
        df_final=df_final[df_final["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

        for u in df_final.unittype.unique():
            plot_df = df_final[df_final.unittype == u]
            fig.add_trace(
            go.Bar(x=plot_df.scenario, y=plot_df.gen/plot_df.cons*-100, name=u, width=1,marker_color=plot_df.color
            ,text=plot_df.gen/plot_df.cons*-100
            ))
        fig.update_traces(texttemplate='%{text:.1f}', textposition='inside')

        fig.update_layout(barmode='relative',plot_bgcolor='rgba(0,0,0,0)',autosize=False,
            width=w,height=h,
            font=dict(family=font, color="black",size=14),
            legend=dict(y=0.5,
            traceorder="reversed"
            ), margin=dict(t=10))
        fig.update_layout(uniformtext_minsize=size, uniformtext_mode='hide')
        fig.update_yaxes(linecolor="black",title="Share of electricity generation of annual demand (%)",title_standoff = 0.5,ticks="outside",dtick=10)
        fig.update_xaxes(linecolor="black",tickangle = 90)
        fig.add_hline(y=0,line_width=0.5)
        if not image:
            pass
        else:
            fig.write_image(image,scale=5,height=h,width=w)
        return fig



    def plot_totalgenshare_bb3(self,grid='elec',category=[],w=500,h=500,unitlist=[],image=[]):
        df_final=pd.DataFrame()
        colors=pd.DataFrame(self.color_dict.items(), columns=['unittype', 'color'])
        for s, r, in zip(self.scenarios, self.bb_results):
            r_genByUnittype_gn = r.param_as_df("r_genByUnittype_gn").rename(columns={"value": "gen"})
            df=r_genByUnittype_gn[r_genByUnittype_gn.grid == grid]
            df["unittype"][df["unittype"]=="Wind Onshore New 1"]="Wind Onshore High FLH"
            df["unittype"][df["unittype"]=="Wind Onshore New 2"]="Wind Onshore High MV"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel","Others"]) else 0)==1]="Other thermal renewables"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr","CSP","ror","PHS"]) else 0)==1]="Other non-thermal renewables"
            df=df[df["gen"]>0]
            df=df.groupby(["unittype","grid"])["gen"].sum().reset_index()
            r_gTotalConsumption=r.param_as_df("r_gTotalConsumption").rename(columns={"value": "cons"})
            r_gTotalConsumption=r_gTotalConsumption[r_gTotalConsumption["grid"]==grid]
            if grid == "pros":
            #    df2["cons"]=df2["cons"].apply(lambda x: x-df[df.unittype=="aggregator"]["gen"].values[0])
                df.loc[df["unittype"]=="Solar PV rooftop","gen"]=df[df.unittype=="Solar PV rooftop"]["gen"].apply(lambda x: x+df[df.unittype=="aggregator"]["gen"].values[0])
            #else:
            #    continue

            #df[df.grid=="pros"]["gen"].apply(lambda x: abs(x))
            #sum up some stuff as "other"
            df=pd.merge(df,colors,on="unittype")
            df=pd.merge(df,r_gTotalConsumption,on="grid")
            #change wind onshore color
            #df["color"][df["unittype"]=="Wind Onshore"]="darkgrey"
            #df=df[df["gen"]>0]
            
            #rename stuff
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 plant"]) else 0)==1]="H2 CCGT"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 electrolyser"]) else 0)==1]="Electrolyser"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["H2 turbine"]) else 0)==1]="H2 Turbine"
           # df["type"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["Batteries"]) else 0)==1]="Batteries"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["dsr"]) else 0)==1]="Demand-Side Response"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["biofuel"]) else 0)==1]="Biofuel"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ror"]) else 0)==1]="ROR"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["aggregator"]) else 0)==1]="Prosumer Feed-In"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["PHS"]) else 0)==1]="Pumped Hydro Storage"
            df["unittype"][df["unittype"].apply(lambda x: 1 if any(i in x for i in ["ev"]) else 0)==1]="EV"

            #sort stuff
            df["cat"]="b"
            df["cat"][df["unittype"]=="H2 Turbine"]="c"
            df["cat"][df["unittype"].apply(lambda x: 1 if any(i in x for i in category) else 0)==1]="a"
            #df=df[df["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]
            df["scenario"]=str(s)
            df_final=pd.concat([df,df_final])
            df_final=df_final.sort_values(["cat","unittype","scenario"])
        fig = go.Figure()

        #choose unittypes
        if not unitlist:
            unitlist=df_final.unittype.unique()
        df_final=df_final[df_final["unittype"].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

        for u in df_final.unittype.unique():
            plot_df = df_final[df_final.unittype == u]
            fig.add_trace(
            go.Bar(x=plot_df.scenario, y=plot_df.gen/plot_df.cons*-100, name=u, width=1,marker_color=plot_df.color
            ,text=plot_df.gen/plot_df.cons*-100
            ))
        fig.update_traces(texttemplate='%{text:.1f}',textposition='outside')
        fig.update_layout(barmode='relative',plot_bgcolor='rgba(0,0,0,0)',autosize=False,
            width=w,height=h,
            font_family="Open Sans", font_color="black",
            legend=dict(
            y=0.5,
            ))
        fig.update_yaxes(linecolor="black",title="Share of electricity generation of annual demand (%)",title_standoff = 0.5,ticks="outside",dtick=10)
        fig.update_xaxes(linecolor="black",tickangle = 90)
        fig.add_hline(y=0,line_width=0.5)
        if not image:
            pass
        else:
            fig.write_image(image,scale=5,height=h,width=w)
        return fig




    #Generation share by type and node - seperate storage discharge plot
    def plot_genShare_nodes(self, colors=None,grid='elec'):
        for s, r in zip(self.scenarios, self.bb_results):
            r_gnuTotalGen_unittype = r.param_as_df("r_gnuTotalGen_unittype").rename(columns={"value": "gen"})
            r_gnuTotalGen_unittype = r_gnuTotalGen_unittype[r_gnuTotalGen_unittype["grid"]=="elec"]
            r_gnTotalConsumption = r.param_as_df("r_gnTotalConsumption").rename(columns={"value": "cons"})
            r_gnTotalConsumption = r_gnTotalConsumption[r_gnTotalConsumption["grid"]=="elec"]
            df=r_gnuTotalGen_unittype.merge(r_gnTotalConsumption, on=['node', 'grid'])
            df["unittype"][df["unittype"]=="biofuel"]="Biofuel"
            df["unittype"][df["unittype"]=="dsr"]="DSR"
            df["unittype"][df["unittype"]=="ror"]="ROR"
            df["unittype"][df["unittype"]=="H2 turbine"]="H2 Turbine"

            list=["Batteries Discharge", "PHS Discharge", "H2 Turbine"]
            df_stor=df[df["unittype"].apply(lambda x: 1 if any(i in x for i in list) else 0)==1]
            df_stor["genshare"]=df_stor["gen"]/df_stor["cons"]*-100
            df_stor["type"]=" "
            df_stor["sorter"]="a"
            list=[ "H2", "Batteries", "PHS"]
            df_elec=df[df["unittype"].apply(lambda x: 0 if any(i in x for i in list) else 1)==1]
            df_elec["genshare"]=df_elec["gen"]/df_elec["cons"]*-100
            df_elec["type"]="  "
            df_elec["sorter"]="b"
            df=pd.concat([df_elec,df_stor])
            df["node"]=df["node"].map(lambda x: str(x)[:2])
            df=df.sort_values(["sorter","node"])

            fig = go.Figure()

            x=[df.node,df.type]

            for u in df.unittype.unique():
                plot_df = df[df.unittype == u]
                fig.add_trace(
                go.Bar(x=[plot_df.node, plot_df.type], y=plot_df.genshare, name=u, marker_color=self.color_dict[u], width=1
                ))
            fig.update_layout(barmode='relative',plot_bgcolor='rgba(0,0,0,0)',yaxis_range=[0,100],autosize=False,
                width=800,
                height=500, font_family="Open Sans", font_color="black",legend=dict(y=0.5))
            fig.update_yaxes(linecolor="black",dtick=20,title="%",title_standoff = 0.5)
            fig.update_xaxes(linecolor="black")
            return fig




    #plot capacities
    def plot_capa_nodes_scen(self,nodelist=[],unitlist=[]):
        df_final=pd.DataFrame()
        for s, r in zip(self.scenarios,self.bb_results):
            p_gnu_io=r.param_as_df("p_gnu_io")
            p_unit=r.param_as_df("p_unit")

            unitUnittype=r.set_as_df("unitUnittype")

            #dataframe for existing capacity
            df_ex=pd.DataFrame()
            input1_=p_gnu_io[p_gnu_io["param_gnu"]=="capacity"]
            df_ex["capacity"]=input1_["value"]      
            df_ex["unit"]=input1_["unit"]
            df_ex["node"]=input1_["node"]
            av=p_unit[p_unit["param_unit"]=="availability"]
            df_ex=pd.merge(df_ex,av,on="unit")
            df_ex["capacity"]=df_ex["capacity"]*df_ex["value"]
            df_ex=df_ex.drop(["value","param_unit"],axis=1)

            df_ex=pd.merge(df_ex,unitUnittype,on="unit")
            df_ex=df_ex[df_ex['unit'].apply(lambda x: 1 if any(i in x for i in ["New"]) else 0)==0]
            df_ex=df_ex[df_ex['node'].apply(lambda x: 1 if any(i in x for i in ["elec","pros"]) else 0)==1]

            r_invest=r.r_invest()
            r_invest["capacity"]=r_invest['Val']
            r_invest.pop("Val")
            r_gnuTotalGen=r.param_as_df("r_gnuTotalGen")
            r_gnuTotalGen=r_gnuTotalGen[r_gnuTotalGen['node'].apply(lambda x: 1 if any(i in x for i in ["elec","pros"]) else 0)==1]

            #totalgen=r_gnuTotalGen.groupby(["node"]).sum().reset_index()
    
            merge=r_gnuTotalGen[["node","unit"]]
            df_new=pd.merge(r_invest,merge,on=["unit"])
            df_new=df_new[df_new['node'].apply(lambda x: 1 if any(i in x for i in ["elec","pros"]) else 0)==1]
            df_new=pd.merge(df_new,unitUnittype,on=["unit"])
            df=pd.concat([df_new,df_ex])
            #df=df[df['node'].apply(lambda x: 1 if any(i in x for i in nodelist) else 0)==1]
            df=df[df['unit'].apply(lambda x: 1 if any(i in x for i in unitlist) else 0)==1]

            df=df[df['unit'].apply(lambda x: 1 if any(i in x for i in ["Charge"]) else 0)==0]
            df=df[df['unit'].apply(lambda x: 1 if any(i in x for i in ["electrolyser"]) else 0)==0]
            # df=df[df['unit'].apply(lambda x: 1 if any(i in x for i in ["aggregator"]) else 0)==0]
            # df=df[df['unit'].apply(lambda x: 1 if any(i in x for i in ["supplier"]) else 0)==0]

            #df=pd.merge(df,totalgen,on=["node"])
            df["capacity"]=df["capacity"]/df_final["value"]*1000
            ##if not nodelist:
            #    nodelist=df['node'].drop_duplicates().to_list()
            #df=df[df['node'].apply(lambda x: 1 if any(i in x for i in nodelist) else 0)==1]
            df["node"]=df["node"].map(lambda x: str(x)[:-5])     
            print(df) 
            df=df.groupby(['unittype','node']).sum().reset_index()
            df["scen"]=str(s)
            df_final=pd.concat([df,df_final])

        df_final=df_final.sort_values(["node","scen"])

        fig=go.Figure()
        for u in df_final.unittype.unique():
            plot_df = df_final[df_final.unittype == u]
            fig.add_trace(
            go.Bar(x=[plot_df.node,plot_df.scen], y=plot_df.capacity, 
            name=u, 
            marker_color=self.color_dict[u]
            ))
        fig.update_layout(barmode='stack',plot_bgcolor='rgba(0,0,0,0)',legend=dict(
            y=0.5),width=1500,
                height=600,)
        fig.update_yaxes(linecolor="black",title="GW",title_standoff = 0.5
        #dtick=20,
        )
        fig.update_xaxes(linecolor="black")
        return fig


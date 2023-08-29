#!/usr/bin/env python
# coding: utf-8

# # Tableau de bord

# In[1]:
import logging


admin_logger = logging.getLogger('panel')
logger = logging.getLogger('analogs')
logger.setLevel(logging.INFO)
logger.addHandler(admin_logger)

import time
t0 = time.time()
def update_time(msg=""):
    global t0
    t1 = time.time()
    logger.debug(msg + str(t1 - t0))
    t0 = t1
def reset_time():
    global t0
    t0 = time.time()
    
# In[3]:


import json
from pathlib import Path
import panel as pn


from core import utils
global config
config = pn.state.as_cached('config',utils.load_config)
app_title = {"en":"Climate Analogues","fr":"Analogues climatiques"}

LOCALE = "en"
qd = {}
show_header = True
show_modal = True

if hasattr(pn,'state') and hasattr(pn.state,'location') and pn.state.location and hasattr(pn.state.location,'query_params'):
    qd = pn.state.location.query_params

if ('lang' in qd) and (qd['lang'] in ['en','fr']):
  LOCALE = qd['lang']
  print("LOCALE registered.",LOCALE)
  show_header = False
  show_modal = False
    
## Set CSS:
# Related to integration in CCDP

css = "" if show_header else """
nav#header {
    display: None;
}

div#sidebar {
    box-sizing: border-box;
    height: 100%;
}

div#main {
    box-sizing: border-box;
    height: 100vh;
}
"""

css += """
.bk-root .choices__list--dropdown .choices__item--selectable {
		padding-right: 10px;
}
.bk-root .choices__list--multiple .choices__item,
.bk-root .choices__list--dropdown {
		word-break: unset;
	  overflow-wrap: break-word;
}
div#main .pn-loading::before {
    background-position: top center;
}"""
js_files = {
    "main": "./scripts/main.js"
}

pn.extension(
    raw_css=[config["css"].replace('\\n','').replace('\n',''), css],
    js_files=js_files,
    loading_spinner='arcs',
    loading_color='#3869f6'
)

## First load: just the dashboard, help buttons, and language.
dash = pn.template.VanillaTemplate(title='', sidebar_width=350)

sidebar = pn.FlexBox(align_content='flex-start',justify_content='flex-start', flex_wrap='nowrap', flex_direction='column', sizing_mode='stretch_both', css_classes=['flex-sidebar'])
main    = pn.FlexBox(align_content='flex-start',justify_content='center', flex_wrap='nowrap', flex_direction='column', sizing_mode='stretch_width')
modal   = pn.FlexBox(align_content='space-evenly',justify_content='space-evenly', flex_wrap='nowrap', flex_direction='column', sizing_mode='stretch_both')
header  = pn.FlexBox(align_content='space-evenly',justify_content='space-evenly', flex_wrap='nowrap', flex_direction='column', sizing_mode='stretch_both')

dash.sidebar.append(sidebar)
dash.main.append(main)
dash.modal.append(modal)
dash.header.append(header)

    
w_sidetitle = pn.pane.Markdown({'en':'##Loading app...','fr':'##Téléchargement...'}[LOCALE],css_classes=['sidebar-title'])
sidebar.append(w_sidetitle)
w_loading_spinner = pn.indicators.LoadingSpinner(height=100,width=100,value=True,color="primary")
w_loading_text = pn.panel({'en':'Loading app...','fr':'Téléchargement...'}[LOCALE],
                   style={'background-color':'var(--primary)','color':'white','border-radius':'25px',"padding-left":"10px","padding-right":"10px"})
w_loading = pn.Column(w_loading_spinner, w_loading_text)

sidebar.append(pn.Row(pn.layout.HSpacer(),w_loading,pn.layout.HSpacer()))

main.append(pn.Column(pn.layout.VSpacer(),w_loading,pn.layout.VSpacer()))

docpath = Path('./docs')
docs = {}
if docpath.is_dir():
    for file in docpath.glob('*.md'):
        with open(file,'r') as f:
            docs[file.stem] = f.read()
## MODAL: 
w_enter_en = pn.widgets.Button(name='Enter')
w_enter_fr = pn.widgets.Button(name='Entrer')
w_enter_en.disabled = True
w_enter_fr.disabled = True

w_about_en = pn.Column(pn.pane.Markdown(docs['info_en'],width=350), w_enter_en,pn.layout.VSpacer(height=42))
w_about_fr = pn.Column(pn.pane.Markdown(docs['info_fr'],width=400), w_enter_fr,pn.layout.VSpacer(height=42))
modal_lang = pn.Row(pn.layout.HSpacer(),w_about_en,pn.layout.HSpacer(),w_about_fr,pn.layout.HSpacer(),min_width=700)
modal.append(modal_lang)

def open_modal(event):
    dash.open_modal()
    
## HEADER:
w_about_name = {"en":"About","fr":"À Propos"}
w_open_modal = pn.widgets.Button(name=w_about_name[LOCALE], width = 150)
w_open_modal.on_click(open_modal)



    
w_language = pn.widgets.Button(name="Français", width=150)
w_title = pn.pane.HTML(f'''<div class="title">{app_title[LOCALE]}</div>''')
w_headerbox = pn.Row(w_title,pn.layout.HSpacer(),w_open_modal)
header.append(w_headerbox)

update_time('time to first load: ')


# In[4]:

def get_helppage(locale):
    docpages = {'howto':{"en":"How to use this app","fr":"Comment utiliser cette application"},
                'interp':{"en":"Interpreting Results","fr":"Interprétation des résultats"},
                'advanced':{"en":"Advanced Options","fr":"Options avancées"},
                'attribution':{"en":"Attribution and Sources","fr":"Attribution et Sources"}
               }
    docpage_locale = {k+'_'+locale:v[locale] for k,v in docpages.items()}
    markdowns = [pn.pane.Markdown(object=f'<div id="{k}"/>\n'+ docs[k],sizing_mode='stretch_width',max_width=920,width_policy='max') for k,v in docpage_locale.items()]
    linkhtml_en = ''.join(["<h1>Help</h1><h2>Contents:</h2><table class='link-table'>",*[f'<tr><td><a href="#{page}">{i+1}– {title}</td></tr>' for i,(page,title) in enumerate(docpage_locale.items())],"</table>"])
    linkhtml_fr = ''.join(["<h1>Aide</h1><h2>Contenu:</h2><table class='link-table'>",*[f'<tr><td><a href="#{page}">{i+1}. {title}</td></tr>'  for i,(page,title) in enumerate(docpage_locale.items())],"</table>"])

    links = pn.pane.HTML({"en":linkhtml_en,"fr":linkhtml_fr}[locale],sizing_mode='stretch_width',max_width=920,width_policy='max')
    w_about = pn.pane.Markdown(docs[f'info_{locale}'],max_width = 920,width_policy='max')
    
    helppage = pn.Column(name={"en":"Help","fr":"Aide"}[locale],max_width=920, width_policy='max')
    helppage.append(w_about)
    helppage.append(links)
    [helppage.append(markdown) for markdown in markdowns]
    w_report_download = pn.widgets.FileDownload(file="analogs_report_202205.pdf",
                                                label={"en":"Download full report","fr":"Télécharger rapport (en)"}[locale],
                                                width=300)
                                                
    helppage.append(pn.Row(pn.layout.HSpacer(),w_report_download,pn.layout.HSpacer()))
    helppage.append(pn.layout.VSpacer(height=50))
    return helppage


# In[5]:


# panel has difficulty with local modules, it seems.

from core import utils, widgets, search
from core.constants import (fut_col, 
                            hist_col, 
                            ana_col, 
                            quality_terms_en, 
                            quality_terms_fr, 
                            quality_colors, 
                            best_analog_mode, 
                            analog_modes, 
                            analog_modes_desc, 
                            cache_path, 
                            WRITE_DIR, 
                            benchmark_path, 
                            density_path,
                            maxpts,
                            minpts,
                            min_density
                           )
import os

if not WRITE_DIR.exists():
    os.makedirs(WRITE_DIR,exist_ok=True)
    
main.clear()
searches = widgets.TabsMod(get_helppage(LOCALE),closable=True, dynamic=True)
searches.closablelist[0] = False
main.append(searches)


# In[14]:


try_again = pn.widgets.Button(name="Try again?",width=300,button_type='danger')

def update_handled(language=LOCALE):
    try:
        return update_dashboard(language)
    except Exception as e:
        # change to "app not available", change color.
        w_loading.clear()
        error_text=pn.panel("Error loading app...",
                           style={'background-color':'#A00','color':'white','border-radius':'25px',"padding-left":"10px","padding-right":"10px"})
        error_cause=pn.panel("Error Log: "+str(type(e)) + "\n" + str(e))
        
        w_loading.append(pn.FlexBox(error_text,error_cause,try_again,flex_direction='column',align_items='center'))
        logger.error(str(e))
        
try_again.on_click(update_handled)

def update_dashboard(language=LOCALE):
    ''' these modules are heavy to load the first time, defering their import can help.'''
    
    # Paquets
    from collections import namedtuple
    
    from io import StringIO
    import numpy as np
    import pandas as pd
    from panel.viewable import Viewer
    from bokeh.models import HoverTool, TapTool
    import param
    
    from datetime import datetime
    import pickle
    import joblib
    import warnings
    from shapely.errors import ShapelyDeprecationWarning
    from bokeh.events import Tap
    
    warnings.filterwarnings("ignore",category=ShapelyDeprecationWarning)
    
    update_time("time to import: ")
    
    global cities, dref, dsim, biasadjust, init_rand_city, benchmark, density, places, datavars

    # Dask. To make this dashboard slightly faster, change the "scheduler" argument to scheduler='processes' and num_workers=4 (for example)
    # However the final webapp most likely won't have access to this kind of parallelism
    import dask
    dask.config.set(scheduler=config["options"]["dask_schedule"], temporary_directory='/notebook_dir/writable-workspace/tmp')
    try:
        curr_dir = Path(__file__).parent
    except NameError:  # When running as a notebook "__file__" isn't defined.
        curr_dir = Path('.')
    cities_file = curr_dir / Path('cities_tmp.geojson')
    
    # Projection
    biasadjust = config["options"]["biasadjust"] # scaling or dqm the method used for the annual adjustment method

    # Random city on load
    init_rand_city = config["options"]["init_rand_city"]

    def set_toolbar_autohide(plot, element):
        bokeh_plot = plot.state
        bokeh_plot.toolbar.autohide = True
                        
    cities = pn.state.as_cached('cities',utils.load_cities)
    w_city = pn.widgets.MultiChoice(
        name={"en":'Target city',"fr":"Ville ciblée"}[language],
        options={f"{city.prov_code}: {city.city}": i for i, city in cities.iterrows()},# autosorts due to bug in bokeh, need to have prov_code first.
        width=300,min_width=300,max_width=300,
        max_items=1
    )
    #if init_rand_city:
    #    def random_city():
    #        w_city.value = np.random.randint(0, len(cities))
    #
    #    pn.state.onload(random_city)
    
    w_col_city = pn.Column(w_city)
    
    w_ssp = pn.widgets.RadioButtonGroup(
                    options = {{"en":"Moderate (SSP2-4.5)","fr":"Modérées (SSP2-4.5)"}[language]:"ssp245",
                               {"en":"High (SSP5-8.5)",    "fr":"Élevées (SSP5-8.5)"}[language]:"ssp585"
                              },
                    sizing_mode='stretch_width',width_policy='max')
    w_ssp_labelled = pn.Column({"en":'Emissions scenario:',"fr":"Scénario d'émissions :"}[language],w_ssp, width=300,min_width=300,max_width=300)
                  
    
    
    w_tgt_period = pn.widgets.DiscreteSlider(
        name={"en":'Target period',"fr":"Période ciblé"}[language],
        options={{"en":f"{x-29}-{x}","fr":f"{x-29} à {x}"}[language]: slice(f"{x-29}", f"{x}") for x in range(2020, 2101, 10)},
        value=slice("2041", "2070"), width=300,min_width=300,max_width=300
    )
    datavars = pn.state.as_cached('datavars',utils.load_datavars)
    w_indices = pn.widgets.MultiChoice(
        name={"en":'Climate indices (select up to 4)',"fr":"Indices climatiques (sélectionner jusqu'à 4)"}[language],
        max_items=4,
        options={v[language]: k for k, v in datavars.items()},
        width=300,min_width=300,max_width=300
    )
    
    @pn.depends(icity=w_city, ssp=w_ssp, tgt_period=w_tgt_period.param.value_throttled)
    def usable_indices(icity, ssp, tgt_period):
        if icity:
            with pn.param.set_values(w_indices, loading=True):
                
                
                unusable = search.get_unusable_indices(icity[0], ssp, tgt_period)
                options = {v[language]: k for k, v in datavars.items() if k not in unusable}
                values = [v for v in w_indices.value if (v not in unusable) and (v in datavars)]
                w_indices.options = options
                w_indices.value = values
        #if unusable:
        #    return pn.pane.Alert(
        #        "Some indices are not usable for this combination of city, scenario and target period.",
        #        alert_type='warning'
        #    )
        return pn.pane.Str('',visible=False)


    w_density_factor = pn.widgets.IntSlider(name={"en":'Density range factor',"fr":"Facteur de densité"}[language], value=4, step=1, start=2, end=10,width=280)

    @pn.depends(icity=w_city, density_factor=w_density_factor)
    def info(icity, density_factor):
        if icity:
            dens = cities.iloc[icity[0]].density
            #dmin = max(dens / density_factor, min_density)
            #dmax = dens * density_factor
            density = pn.state.as_cached('density',utils.load_density)
            
            mask = utils.getmask(density,density_factor,dens,minpts,maxpts,min_density)
            N = mask.sum().item()
            dmask = density.where(mask)

            dmin = dmask.min()
            dmax = dmask.max()
            return pn.pane.Markdown(
                {"en": f"* Target population density : {dens:.0f} people per km²\n"
                        f"* Population density range : {dmin:.0f} - {dmax:.0f} people per km²\n"
                        f"* Number of search candidates : {N}",
                 "fr":f"* Densité de la ville ciblée : {dens:.0f} hab./ km²\n"
                        f"* Densités admissibles : {dmin:.0f} - {dmax:.0f} hab. / km²\n"
                        f"* Nombre de candidats de recherche : {N}"
                }[language],width=260
            )
        else:
            return pn.pane.Markdown('  ',width=260)
    w_show_poor = pn.widgets.Checkbox(name={"en":"Display poor quality analogues","fr":"Montrer les analogues de faible qualité"}[language],value=False,width=280)
    w_run = pn.widgets.Button(name="",min_width=300, max_width=300,width=300)
    
    w_analog_mode = pn.widgets.Select(options={analog_modes_desc[language][i]:x for i,x in enumerate(analog_modes)},
                                      value=best_analog_mode,
                                      name={"en":"Choice of analogue","fr":"Choix d'analogue"}[language], width=260)
    w_num_real  = pn.widgets.IntSlider(name={"en":"Number of climate simulations","fr":"Nombre de simulations climatiques"}[language],start=6,end=24,step=1,value=12, width=280)
    
    w_progress = pn.widgets.Progress(active=False, min_width=300, width=300,bar_color='primary') # Progress(active=False, delta=0.1, min_width=200, width=300)
    sort_options = ["ana","x","rep"]
    sortopts_desc = {"en":["Prioritize analogue quality over representativeness","Balanced sorting","Prioritize representativeness over analogue quality"],
                     "fr":["Prioriser la qualité d'analogues sur la représentativité","Trie balancée","Prioriser la représentativité sur la qualité d'analogues"]}
    w_sort = pn.widgets.Select(options={sortopts_desc[language][i]:x for i,x in enumerate(sort_options)},
                               value='x',name={"en":"Sorting display option","fr":"Trie de l'affichage"}[language], width=260)
    
    @pn.depends(indices = w_indices, icity=w_city,tabs=searches.param['objects'])
    def enable_search(indices,icity,tabs):
        dummy_pane = pn.pane.Str('',visible=False)
        if not icity:
            w_run.disabled = True
            w_run.name = {"en":"Select a target city!","fr":"Sélectionner une ville cible !"}[language]
            return dummy_pane
        if len(tabs) > 5:
            w_run.disabled = True
            w_run.name = {"en":"Too many tabs open.\nClose tabs to continue.","fr":"Trop de recherches ouvertes.\nFermer des onglets."}[language]
            return dummy_pane
        if not indices:
            w_run.disabled = True
            w_run.name = {"en":"Select some climate indices!","fr":"Sélectionner des indices climatiques !"}[language]
            return dummy_pane
        w_run.disabled = False
        w_run.name = {"en":"Run analogues search","fr":"Exécuter la recherche d'analogues"}[language]
        return dummy_pane
    
    #@pn.depends(clicks=w_run.param.clicks)
    def analogs_search(clicks):
        """This function does everything."""
        w_progress.active = True
        
        if clicks == 0:
            return pn.pane.Str({"en":'Please run an analogue search using the sidebar.',"fr":"Faites une nouvelle recherche avec la barre de gauche."}[language])
        # imports:
        reset_time()
        import holoviews as hv
        import geopandas as gpd
        import geoviews as gv
        from shapely.geometry import Point, LineString
        from clisops.core.subset import distance
        
        update_time("search, imports: ")
        # data:
        dref = pn.state.as_cached('dref',utils.load_dref)
        dsim = pn.state.as_cached('dsim',utils.load_dsim)
        benchmark = pn.state.as_cached('benchmark',utils.load_benchmark)
        density = pn.state.as_cached('density',utils.load_density)
        places = pn.state.as_cached('places',utils.load_places)
        update_time("search, data load: ")
        gv.extension('bokeh')
        CartoLabels = gv.element.WMTS('https://a.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}@2x.png', name='CartoLabels')
        CartoBase = gv.element.WMTS('https://cartodb-basemaps-4.global.ssl.fastly.net/light_nolabels/{Z}/{X}/{Y}@2x.png', name="CartoBase")

        CDNLabelsEn = gv.element.WMTS('https://maps-cartes.services.geo.ca/server2_serveur2/rest/services/BaseMaps/CBMT_TXT_3857/MapServer/WMTS/tile/1.0.0/BaseMaps_CBMT_TXT_3857/default/default/{z}/{y}/{x}.png', name='CDNLabelsEn')
        CDNLabelsFr = gv.element.WMTS('https://maps-cartes.services.geo.ca/server2_serveur2/rest/services/BaseMaps/CBCT_TXT_3857/MapServer/WMTS/tile/1.0.0/BaseMaps_CBMT_TXT_3857/default/default/{z}/{y}/{x}.png', name='CDNLabelsFr')
        EsriTopo = gv.element.WMTS('https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{Z}/{Y}/{X}@2x', name="EsriTopo").opts(alpha=0.5, max_zoom=8)

        LabelMap = CartoLabels if (language == "en") else CartoLabels

        
        # Translate the widget's values to variables
        # The goal is to keep the code here and in the notebook in sync so that copy-pasting the main parts doesn't break
        icity = w_city.value[0]
        ssp = w_ssp.value
        ssp_opts = dsim.ssp.values
        tgt_period = w_tgt_period.value
        periods = list(w_tgt_period.options.values())
        climate_indices = w_indices.value
        density_factor = w_density_factor.value
        max_density = w_density_factor.end
        show_poor = w_show_poor.value
        best_analog_mode = w_analog_mode.value
        analog_mode = list(w_analog_mode.options.values())
        n_real = w_num_real.value
        max_real = w_num_real.end
        ana_sort = w_sort.value
        
        ### Analogue finding begins here. Code below should be the exact same as in the notebook
        city = cities.iloc[icity]

        #sim = dsim[climate_indices].isel(location=icity).sel(ssp=ssp)
        #global analogs
        update_time("search, constants: ")
        logger.info(f"Searching for analogues for {city.city}, ind:{climate_indices}, ssp:{ssp}, end-yr: {tgt_period.stop}")
        analogs, sim, ref = search.analogs(dsim, 
                                                  dref, 
                                                  density, 
                                                  benchmark, 
                                                  city,cities,places, 
                                                  climate_indices, 
                                                  density_factor,max_density, 
                                                  tgt_period,periods, 
                                                  ssp,ssp_opts,
                                                  best_analog_mode,analog_modes,
                                                  n_real,max_real)
        update_time("search, inner: ")
        if not show_poor:
            filter_rows = np.where(analogs['qflag'] > 2)[0]
            if len(filter_rows) < analogs.shape[0]:
                analogs.drop(filter_rows, inplace = True)
        
        if ana_sort == 'x':
            analogs['mult'] = analogs['zscore'] * analogs['percentile']
            analogs = analogs.sort_values('mult').reset_index(drop=True).drop(columns='mult')
        elif ana_sort == 'ana':
            analogs = analogs.sort_values('percentile').reset_index(drop=True)
        elif ana_sort == 'rep':
            analogs = analogs.sort_values('zscore').reset_index(drop=True)
        #analogs['rank'] = analogs.index + 1
        
        selector = widgets.ColoredToggleGroup(analogs.quality_en)

        

        point_opts = {'color':('quality_en' if (language == 'en') else 'quality_fr'), 
                      'marker':'circle',
                      'size':10, 
                      'cmap':dict(zip(quality_terms_en if (language == 'en') else quality_terms_fr, quality_colors)), 
                      'line_color':'k'}

        # Map of analogues
        @pn.depends(iana=selector.param.value)
        def chosen_point(iana):
            return gv.Points(analogs.iloc[[iana]])
        
        analogs_lines = gpd.GeoDataFrame(
            analogs.drop(columns=['geometry']),
            geometry=[LineString([city.geometry, geom]) for geom in analogs.geometry]
        )

        shown_dims_en = ['@simulation','@near','@quality_en','@rank']
        shown_dims_fr = ['@simulation','@near','@quality_fr','@rank']
        shown_dims_labels_en = ['Simulation','Near','Analogy Quality','Representation Rank']
        shown_dims_labels_fr = ['Simulation','Près de', "Qualité d'analogie", 'Rang de représentation']
        # plot tools for point_map:
        tooltips = zip(shown_dims_labels_en,shown_dims_en,) if (language == 'en') else zip(shown_dims_labels_fr,shown_dims_fr,)

        hover = HoverTool(tooltips=list(tooltips))
        point_source = analogs.sort_values(by=['qflag','zscore']).reset_index()
        tap = TapTool()
        def on_click(event):
            # took me way too long to find the right transform...
            (lon,lat) = hv.util.transform.easting_northing_to_lon_lat(event.x,event.y)
            dists = distance(point_source.drop(columns=['geometry']).to_xarray(),lon=lon,lat=lat) / 1000.
            ind = dists.argmin()
            if (dists[ind] < 200):
                selector.value = int(point_source.iloc[int(ind)]['index'])

        def hook(plot,element):
            plot.state.on_event(Tap, on_click)
        # reverse order so that best points are plotted on top (last).
        point_map =  gv.Points(point_source[::-1]).opts(tools=[hover,tap],hooks=[hook],nonselection_alpha=1,**point_opts)
        
        analog_map =  pn.pane.HoloViews(
            (
                CartoBase
                * EsriTopo
                * LabelMap
                * gv.Path(analogs_lines).opts(nonselection_alpha=1)
                * gv.Points([city.geometry]).opts(color=fut_col, marker='star', size=15)
                * point_map
                * gv.DynamicMap(chosen_point).opts(color=ana_col, marker='circle', fill_color='none', size=20, line_width=4)
                * gv.DynamicMap(chosen_point).opts(show_legend=False,clabel=None,**point_opts)
            ).opts(width=600, height=550, title={"en":'Map of analogues',"fr":"Carte d'analogues"}[language],hooks=[set_toolbar_autohide]),
            max_width=600,sizing_mode='scale_width',width_policy='max',min_width=600
        )
        # Cards
        
        cards = pn.Accordion(max_width=920,sizing_mode='stretch_width',width_policy='max', header_background='white',
                                  background='white',
                                  active_header_background='white',css_classes=['accordion-univariate'],)
        climdict = {}
        for climind in climate_indices:
            long_name = {"en":sim[climind].long_name,"fr":sim[climind].long_name_fr}[language]
            climdict[long_name] = climind
            name = long_name
            data = pn.Column(name=name, min_height=900, max_width=920,sizing_mode='stretch_width',width_policy='max')
            cards.append(data)

        
        @pn.depends(show=cards.param.active, iana=selector.param.value)
        def get_card_data(show,iana):
            
            for i,panelcard in enumerate(cards.objects):
                if i not in show:
                    panelcard.visible = False
                    #panelcard.min_height=0
                    #panelcard.height = 0
            if not show:
                return cards
            else:
                import hvplot.xarray
                import xclim as xc
                from xclim import analog as xa
                for panelcardind in show:
                    panelcard = cards.objects[panelcardind]
                    panelcard.visible = True
                    #panelcard.min_height = 900
                    #panelcard.height = 900

                    computation_needed = not utils.is_computed(ref)
                    if computation_needed:
                        panelcard.clear()
                        panelcard.insert(0,
                                         pn.pane.Markdown({"en":"### Computing univariate statistics...",
                                                           "fr":"### Calcule de statistiques univariés..."}[language],
                                                          max_width=920,sizing_mode='stretch_width',width_policy='max'))
                        w_progress.active = True
                        utils.inplace_compute(ref)
                        w_progress.active = False
                    #print(analogs)
                    #print(iana)
                    
                    analog = analogs.iloc[iana]

                    climind = climdict[panelcard.name]
                    #print(climind)
                    refi = ref[climind].sel(site=analog.site)
                    histi = sim[climind].sel(realization=analog.simulation, time=slice('1991', '2020'))
                    simq = sim[climind].quantile(q=[0.1,0.5,0.9],dim='realization', keep_attrs=True)
                    simt = sim[climind].sel(realization=analog.simulation)
                    #print('calc')
                    if simt.units == 'K':
                        simt = xc.core.units.convert_units_to(simt,'degC')
                        simq = xc.core.units.convert_units_to(simq,'degC')
                        refi = xc.core.units.convert_units_to(refi,'degC')
                        histi= xc.core.units.convert_units_to(histi,'degC')
                    elif simt.units == 'K days':
                        simt.attrs['units'] =  '°C days'
                        simq.attrs['units'] =  '°C days'
                        refi.attrs['units'] =  '°C days'
                        histi.attrs['units'] = '°C days'
                    simi = simt.sel(time=tgt_period)
                    #print('units')
                    vmin = min(histi.mean() - 3 * histi.std(), refi.min(), simi.min())
                    vmax = max(histi.mean() + 3 * histi.std(), refi.max(), simi.max(), 2 * histi.mean() - vmin)
                    vmin = 2 * histi.mean() - vmax
                    xlim = (float(vmin), float(vmax))
                    #print('xlimits')
                    uni_score = xa.zech_aslan(utils.get_valid(simi), refi)
                    qflag = utils.get_quality_flag(uni_score, [climind], benchmark)
                    
                    units = f"[{simi.units}]".replace('degC','°C') if simi.units else ""
                    name = {"en":simi.long_name,"fr":simi.long_name_fr}[language]
                    name_units = f"{name} {units}"
                    def distr_hook(plot,element):
                        plot.handles['glyph'].hatch_pattern = 'right_diagonal_line'
                        plot.handles['glyph'].hatch_color = fut_col
                        plot.handles['glyph'].hatch_alpha = 1
                        plot.handles['glyph'].hatch_weight = 2
                        plot.handles['glyph'].hatch_scale = 25
                    
                    ana_col,ana_alpha = utils.color_convert_alpha(quality_colors[analog.qflag])
                    #print('colors')
                    dist_diff = (
                        
                        hv.Distribution(simi.values, label={"en":"Target's future","fr":"Ville ciblée dans le futur"}[language]).opts(color=fut_col, fill_alpha = 1)
                        * hv.Distribution(refi.values, label={"en":"Analogue's present","fr":"Analogue dans le présent"}[language]).opts(color=ana_col,fill_alpha=ana_alpha)
                        * hv.Distribution(simi.values, label='').opts(color=fut_col, fill_alpha = 0.2)
                        * hv.Distribution(histi.values, label={"en":"Target's present (click to hide)","fr":"Ville ciblée dans le présent (cliquer pour cacher)"}[language]).opts(hooks=[distr_hook],color='white', line_color='black', fill_alpha=0.5)
                    ).opts(
                        ylabel={"en":'Probability Density',"fr":"Densité de probabilité"}[language], xlabel=name_units,  
                        legend_cols=True, legend_offset=(0, 0), legend_position='bottom', fontscale=1,
                        title={"en":'Distribution comparison',"fr":"Comparaison des distributions"}[language], xlim=xlim,
                        toolbar = 'above', height=300, width=900,
                        hooks=[],
                        default_tools=['save','pan'],
                        fontsize={'title':'25px'}
                    )
                    #print('distrib graph')
                    mean_change = (
                        hv.Overlay(
                            [hv.VLine(histi.quantile([q]).item()).opts(color='darkgrey', line_dash='dashed', alpha=0.8)
                             for q in [0.1,0.25,0.5,0.75,0.9]]
                        ) * hv.Points([[refi.mean().item(), 1]], label="Analogue").opts(color=quality_colors[analog.qflag], size=20, marker='circle')
                        * hv.Points([[histi.mean().item(), 1]], label={"en":"Target's present","fr":"Ville ciblée dans le présent"}[language]).opts(color=hist_col, size=20, marker='star', line_color='k')
                        * hv.Points([[simi.mean().item(), 1]], label={"en":"Target's future","fr":"Ville ciblée dans le futur"}[language]).opts(color=fut_col, size=20, marker='star')
                    ).opts(
                        yaxis=None, xlim=xlim, height=150, width=900, xlabel=name_units,
                        show_legend=False,  #legend_position='bottom', legend_offset=(0, 0), legend_cols=True, 
                        fontscale=1, title={"en":'Average change',"fr":"Changement moyen"}[language], ylabel='nothing', toolbar='above',
                        hooks=[],
                        default_tools=['save'],
                        active_tools = [],
                        tools = [],
                        fontsize={'title':'25px'}
                    )
                    #print('mean change graph')
                    if int(tgt_period.start) >= 2020:
                        refcp = refi.assign_coords(time=simi.time).hvplot(color=quality_colors[analog.qflag]).opts(tools=[], show_legend=False)
                    else:
                        refcp = hv.Overlay()
                             
                    
                    plot_range = hv.Area((simq.time,simq.sel(quantile=0.1),simq.sel(quantile=0.9)),vdims=['y','y2']).opts(tools=[],show_legend=False, color='darkgrey',alpha=0.5,line_width=0)
                    plot_median= simq.sel(quantile=0.5).hvplot(color='darkgrey').opts(tools=[],show_legend=False)
                    #p3 = histi.mean('realization').hvplot().opts(line_color='yellow')
                    timeseries = (
                        (hv.VLine(simi.indexes['time'][0]) * hv.VLine(simi.indexes['time'][-1])).opts(hv.opts.VLine(color='lightblue', line_width=2))
                        * plot_range
                        * plot_median
                        * refi.hvplot(color=quality_colors[analog.qflag], label={"en":'Selected analogue',"fr":"Analogue choisi"}[language])
                        * refcp
                        * simt.hvplot(color=fut_col, label={"en":'Selected simulation on target city',"fr":"Simulation choisi dans la ville ciblée"}[language])
                    ).opts(
                        ylabel=name_units, xlabel='', title={"en":'Full timeseries',"fr":"Série temporelle complète"}[language], legend_position='bottom',
                        show_legend=False, toolbar='above',height=300, width=900,
                        hooks=[],
                        fontsize={'title':'25px'}
                    )
                    #print('timeseries')
                    #print(qflag)
                    #print(quality_terms_en[qflag])
                    description = pn.pane.Markdown(
                        {"en":f"### Quality of univariate analogy: {uni_score: 5.2f} ({quality_terms_en[qflag]})\n"
                        f'- **Description**: {simi.description}\n'
                        f'- **Units** : {units}\n\n',
                         "fr":f"### Qualité de l'analogie univarié: {uni_score: 5.2f} ({quality_terms_fr[qflag]})\n"
                        f'- **Description**: {simi.description_fr}\n'
                        f'- **Unités** : {units}\n\n'
                        }[language],
                        max_width=920,sizing_mode='stretch_width',width_policy='max'
                    )
                    #print('description')
                    panelcard.clear()
                    panelcard.insert(0,description)
                    
                    panelcard.insert(1,pn.pane.HoloViews(dist_diff, linked_axes=False,max_width=920,sizing_mode='stretch_width',width_policy='max'))
                    panelcard.insert(2,pn.pane.HoloViews(mean_change, linked_axes=False,max_width=920,sizing_mode='stretch_width',width_policy='max'))
                    panelcard.insert(3,pn.pane.HoloViews(timeseries, linked_axes=False,max_width=920,sizing_mode='stretch_width',width_policy='max'))
                    #print('appending')
                return cards

        @pn.depends(iana=selector.param.value)
        def summary(iana):
            analog = analogs.iloc[[iana]].to_crs(epsg=8858)


            data = {
                {"en":'Urban area',"fr":"Ville"}[language]: [f"{city.city}, {city.prov_code}", {"en":"near","fr":"près de"}[language] + f" {analog.iloc[0].near} ({analog.iloc[0].near_dist:.0f} km)"],
                {"en":'Coordinates',"fr":"Coordonées"}[language]: [f"{utils.dec2sexa(city.geometry.y)}N, {utils.dec2sexa(-city.geometry.x)}W",
                                f"{utils.dec2sexa(analogs.iloc[iana].geometry.y)}N, {utils.dec2sexa(-analogs.iloc[iana].geometry.x)}W"],
                {"en":"Time period","fr":"Période de temps"}[language]: [f"{tgt_period.start}-{tgt_period.stop}", "1991-2020"],
                {"en":"Data source","fr":"Source de données"}[language]: [f"{analog.iloc[0].simulation} / SSP{ssp[3]}-{ssp[4]}.{ssp[5]}", "ERA5-Land"],
                {"en":"Pop. density","fr":"Densité urbaine"}[language]: [f"{city.density:.0f} hab/km²", f"{analog.iloc[0].density:.0f} hab/km²"]
            }
            perc_fmt = '.0f' if analog.iloc[0].percentile > 1 else ('.2f' if analog.iloc[0].percentile > 0.01 else '.04f')
            return pn.Column(
                pn.pane.Markdown(
                    {"en":f'### Current selection : \#{iana + 1}\n'
                    f'**Quality of analogy**: {analog.iloc[0].quality_en} ({analog.iloc[0].score:.3f}, top {analog.iloc[0].percentile:{perc_fmt}} %)\n\n'
                    f'**Representativeness score**: {analog.iloc[0].zscore:.2f}',
                     "fr":f'### Sélection choisie : \#{iana + 1}\n'
                    f"**Qualité de l'analogie**: {analog.iloc[0].quality_fr} ({analog.iloc[0].score:.3f}, meilleure {analog.iloc[0].percentile:{perc_fmt}} %)\n\n"
                    f'**Score de représentativité**: {analog.iloc[0].zscore:.2f}'
                    }[language]
                ),
                pn.pane.DataFrame(
                    pd.DataFrame.from_dict(data, orient='index', columns=[{"en":'Target',"fr":"Cible"}[language], 'Analogue']),
                ),
                css_classes=['summary-pane'] ,
                max_width=280,
                width_policy='max')
        
        @pn.depends(iana=selector.param.value)
        def export_card(iana):
            import tempfile as tmp
            from io import BytesIO
            import os
            import shutil
            export_name="output.zip"

            # export which analogs:
            export_ana_title={"en":"Select analogues to export:",
                              "fr":"Sélectionner les analogues à exporter :"}[language]
            export_ana_opt = {{"en":"Current analogue","fr":"Analogue actuel"}[language]:"this",
                              {"en":"All analogues","fr":"Tous les analogues"}[language]:"all"}
            export_ana_button = pn.widgets.RadioBoxGroup(options=export_ana_opt,value="this")
            export_ana = pn.Column(export_ana_title,export_ana_button)

            # export which files:
            export_files_title = {"en":"Select files to export:",
                                  "fr":"Sélectionner les fichiers à exporter :"}[language]
            export_files_opt = {{"en":"Summary of analogues","fr":"Sommaire des analogues"}[language]:"analogs",
                                {"en":"Reference timeseries for analogues","fr":"Série temporelle des analogues"}[language]:"ref",
                                {"en":"Projected timeseries for target city","fr":"Série temporelle projetée de la ville ciblée"}[language]:"sim",
                                {"en":"Variable metadata","fr":"Métadonnées des variables"}[language]:"metadata"}
            export_files_button = pn.widgets.CheckBoxGroup(options=export_files_opt,value=['analogs','ref','sim','metadata'])
            export_files = pn.Column(export_files_title,export_files_button)

            # export to what filetype:
            export_filetype_title = {"en":"Select export format:","fr":"Sélectionner le format d'exportation :"}[language]
            export_filetype_opt = {"NetCDF (.nc)":".nc",
                                   ".csv":".csv",
                                   ".json":".json"}
            export_filetype_button = pn.widgets.RadioBoxGroup(options=export_filetype_opt,value=".nc")
            export_filetype = pn.Column(export_filetype_title, export_filetype_button)

            def export_info(file,fmt='.json'):
                ''' exports the xr.dataset attributes to `.json` 
                    or `.csv`, given a file-like object `file`
                '''
                info = {}

                info['reference'] = dref.attrs.copy()
                info['simulation'] = dsim.attrs.copy()
                info['reference']['indices'] = {}
                info['simulation']['indices'] = {}
                for ci in climate_indices:
                    info['reference']['indices'][ci] = dref[ci].attrs.copy()
                    info['simulation']['indices'][ci] = sim[ci].attrs.copy()

                if fmt == '.json':
                    class npEncoder(json.JSONEncoder):
                        def default(self, obj):
                            if not isinstance(obj, str):
                                return str(obj)
                            return json.JSONEncoder.default(self, obj)
                    json.dump(info,file,cls=npEncoder,ensure_ascii=False)
                elif fmt == '.csv':
                    info_flat = pd.json_normalize(info,sep='_')
                    info_flat.transpose().to_csv(file)

            def df_to_file(df,filetype,fileobj):
                if filetype == '.csv':
                    df.to_csv(fileobj)
                elif filetype == '.json':
                    df.to_json(fileobj,force_ascii=False)

            def export_data():
                import dask
                filetype = export_filetype_button.value
                ana_str = export_ana_button.value
                files = export_files_button.value

                tgt_str = f'{tgt_period.start}-{tgt_period.stop}'
                climindstr = '-'.join(climate_indices)
                output_dir = WRITE_DIR / 'export'
                if not output_dir.exists():
                    os.makedirs(output_dir, exist_ok=True)

                filebuffer = BytesIO(b'')

                with tmp.TemporaryDirectory(dir=output_dir) as tmp_dir_path:
                    filenames = []
                    ianas = [iana] if ana_str == 'this' else analogs.index
                    ana = str(iana) if ana_str == 'this' else ana_str
                    sub_anas = analogs.loc[ianas]
                    if 'analogs' in files:
                        filename = Path(tmp_dir_path) / Path(f"analogues_{ana}_summary_{city.city}_{tgt_str}_{ssp}_{climindstr}{filetype}")
                        filename.touch(exist_ok=True)
                        filenames.append(filename)
                        
                        if filetype == '.nc':
                            with open(filename,'wb') as fileobj:
                                ( sub_anas
                                    .to_xarray()
                                    .set_coords(['simulation','lat','lon','ireal','site'])
                                    .drop_vars('geometry')
                                    .to_netcdf(fileobj) )
                        else:
                            with open(filename,'w') as fileobj:
                                df_to_file(sub_anas.drop('geometry',axis=1),filetype,fileobj)
                    if 'ref' in files:
                        filename = Path(tmp_dir_path) / Path(f"analogues_{ana}_ref_{city.city}_{tgt_str}_{ssp}_{climindstr}{filetype}")
                        filename.touch(exist_ok=True)
                        filenames.append(filename)
                        (ref_sites,) = dask.compute(ref.sel(site=sub_anas.site.values))
                        ref_sites = (ref_sites
                                     .assign_coords(realization=('site',sub_anas.simulation.values.astype('<U32')))
                                     .assign_coords(near=('site',sub_anas.near.values.astype('str')))
                                     .set_coords(['realization','lat','lon'])
                                     .swap_dims({"site":"realization"})
                                    )
                        
                        if filetype == '.nc':
                            with open(filename,'wb') as fileobj:
                                ref_sites.to_netcdf(fileobj)
                        else:
                            with open(filename,'w') as fileobj:
                                df = ref_sites.to_dataframe(dim_order=['realization','time'])
                                df_to_file(df,filetype,fileobj)
                    if 'sim' in files:
                        filename = Path(tmp_dir_path) / Path(f"analogues_{ana}_sim_{city.city}_{tgt_str}_{ssp}_{climindstr}{filetype}")
                        filename.touch(exist_ok=True)
                        filenames.append(filename)
                        sim_sites = sim.sel(realization=sub_anas.simulation.values)
                        
                        if filetype == '.nc':
                            with open(filename,'wb') as fileobj:
                                sim_sites.to_netcdf(fileobj)
                        else:
                            with open(filename,'w') as fileobj:
                                df = sim_sites.to_dataframe(dim_order=['realization','time'])
                                df_to_file(df,filetype,fileobj)
                    if 'metadata' in files:
                        filename = Path(tmp_dir_path) / Path(f"analogues_{ana}_metadata_{city.city}_{tgt_str}_{ssp}_{climindstr}{filetype}")
                        if filetype == '.nc':
                            pass # metadata already included in .nc file.
                        else:
                            with open(filename,'w') as fileobj:
                                filename.touch(exist_ok=True)
                                filenames.append(filename)
                                export_info(fileobj,filetype)
                    if len(filenames) > 1:
                        with tmp.TemporaryDirectory(dir=output_dir) as archive_path: 
                            filename = Path(archive_path) / Path(f"analogues_{ana}_{city.city}_{tgt_str}_{ssp}_{climindstr}")
                            # process zipping of file:
                            shutil.make_archive(filename,'zip',tmp_dir_path)
                            filename = filename.with_suffix('.zip')
                            export_button.filename = filename.name
                            with open(filename,'rb') as file:
                                shutil.copyfileobj(file,filebuffer)
                    else:
                        export_button.filename = filename.name
                        with open(filename,'rb') as file:
                            shutil.copyfileobj(file,filebuffer)
                filebuffer.seek(0)    
                return filebuffer

            export_button = pn.widgets.FileDownload(label={'en':"Download file",'fr':"Télécharger"}[language],
                                                    callback=export_data,
                                                    auto=True,
                                                    embed=False,
                                                    button_type='primary',
                                                    filename=export_name)

            note = pn.pane.Markdown({'en':'Note that if selecting more than one file, a .zip file will be generated containing your selection.',
                                     'fr':"Noter que si vous sélectez plus d'un fichier, un fichier .zip sera généré contenant votre sélection."}[language])
            
            export_card = pn.Column(export_ana, 
                             export_files, 
                             export_filetype, 
                             note, 
                             export_button,
                             css_classes=['export-pane'],
                             max_width=280,
                             width_policy='max' )
            
            return export_card
        
        info_card =  pn.Tabs(({"en":'Summary',"fr":"Sommaire"}[language],summary),
                                  ({"en":'Data Export',"fr":"Exportation"}[language],export_card), 
                                  active=0,
                                  css_classes=['info-pane'],
                                  max_width=300,
                                  sizing_mode='stretch_width',
                                  width_policy='max', 
                                  height=550
                            )
        
        @pn.depends(iana=selector.param.value)
        def summary_paragraph(iana):
            analog = analogs.iloc[[iana]].to_crs(epsg=8858)
            cli_ind = list(climdict.keys())
            climate_indices_text = cli_ind[0]
            if len(cli_ind) > 2:
                for ind in range(1,len(cli_ind)-1):
                    climate_indices_text += ', ' + cli_ind[ind]
            if len(cli_ind) > 1:
                climate_indices_text += {"en":" and ","fr":" et "}[language] + cli_ind[-1]
                if language == "en":
                    climate_indices_text = "Based on the climate indices chosen (" + climate_indices_text + ")"
                else:
                    climate_indices_text = "Pour les indices climatiques choisis (" + climate_indices_text + ")"
            else:
                if language == "en":
                    climate_indices_text = "Based on the climate index chosen (" + climate_indices_text + ")"
                else:
                    climate_indices_text = "Pour l'indice climatique choisi (" + climate_indices_text + ")"
            
            climate_sim = analog.iloc[0].simulation
            analog_city = analog.iloc[0].near
            quality = analog.iloc[0].quality_en
            quality_en = f'<span class="quality-word {quality}">' +  quality.lower() + "</span>" + " analogue"
            quality_en = "a" + ("n " if (quality[0].lower() in "aeiou") else " ") + quality_en
            quality_fr = f'<span class="quality-word {quality}">' + analog.iloc[0].quality_fr.lower() + "</span>"
            quality_fr = "un " + quality_fr + " analogue" if (quality.lower() != "average") else "un analogue " + quality_fr
            
            
            highlow = {"en":"high","fr":"élevées"}[language] if ssp == "ssp585" else {"en":"moderate","fr":"modérées"}[language]
            
            target_period = str(tgt_period.start) + {"en":" to ","fr":" et "}[language] + str(tgt_period.stop)
            target_city = city.city
            rank = analog.iloc[0]['rank']
            rank_suffix = ["st","nd","rd","th"][min(rank-1,3)]
            
            repr_score_desc = {"en":(" best " if rank == 1 else f' {rank}{rank_suffix} best '),"fr":(" meilleure " if rank == 1 else f' {rank}e meilleure ')}[language]
            
            text = {"en":(f'''{climate_indices_text}, {analog_city}'s present day climate is {quality_en}'''
                          f''' of the future climate for {target_city}, from {target_period}, under an emissions scenario with {highlow} greenhouse gas emissions.'''
                          f'''This is based on the climate simulation {climate_sim}. Out of the {n_real} simulations chosen, this climate simulation is the'''
                          f'''<span class="rank-word-{rank}">{repr_score_desc}</span>representation of the ensemble mean.'''),
                    "fr":(f'''{climate_indices_text}, le climat actuel de {analog_city} est {quality_fr}'''
                          f''' du climat futur de {target_city}, entre {target_period}, selon un scénario d'émissions de GES {highlow}.'''
                          f''' Ceci est basé sur la simulation climatique {climate_sim}. Sur les {n_real} simulations choisis, cette simulation est la'''
                          f'''<span class="rank-word-{rank}">{repr_score_desc}</span>représentation de la moyenne de l'ensemble.''')
                   }[language]
            
            return pn.pane.HTML(text,max_width=920,sizing_mode='stretch_width',width_policy='max')
        inv_ssp = {v:k for k,v in w_ssp.options.items()}
        w_progress.active = False
        update_time("search, final: ")
        return pn.FlexBox(
            pn.layout.Divider(max_width=565,sizing_mode='stretch_width'),
            selector,
            pn.layout.Divider(max_width=565,sizing_mode='stretch_width'),
            summary_paragraph,
            pn.FlexBox(analog_map, 
                       info_card,
                       flex_direction='row',
                       align_content='flex-start',
                       align_items='flex-end',
                       flex_wrap='wrap-reverse',
                       max_width=910,sizing_mode='stretch_width'
                       ),
            get_card_data,
            pn.layout.VSpacer(height=50,max_height=50),
            name=f'{city.city}, {inv_ssp[ssp]}, {tgt_period.start}-{tgt_period.stop}',
            align_content='center',
            justify_content='flex-start', 
            flex_wrap='nowrap', 
            flex_direction='column', 
            max_width=920,
            sizing_mode='stretch_width',
            width_policy='max'
        )

    advanced_opts = pn.Card(pn.Column(usable_indices,
                                      enable_search,
                                      w_density_factor,
                                      info,
                                      w_show_poor,
                                      w_num_real,
                                      w_analog_mode,
                                      w_sort), collapsed=True, 
                            title={"en":"Advanced options","fr":"Options avancées"}[language],
                            width=300,max_width=300,min_width=300, css_classes=['advanced-card','card'])
    
    sidebar.clear()
    w_enter_en.disabled = False
    w_enter_fr.disabled = False
    w_sidetitle.object = {"en":"##Begin a new search","fr":"##Débuter une nouvelle recherche"}[language]
    sidebar.append(w_sidetitle)
    sidebar.append(w_col_city)
    sidebar.append(w_ssp_labelled)
    sidebar.append(w_tgt_period)
    sidebar.append(w_indices)
    sidebar.append(advanced_opts)
    sidebar.append(w_run)
    sidebar.append(w_progress)
    
    @pn.depends(clicks=w_run.param.clicks, watch=True)
    def t_run(clicks):
        searches.loading = True
        prev = w_run.disabled
        w_run.disabled = True
        pane = analogs_search(clicks)
        
        searches.append(pane)
        w_run.disabled = prev
        searches.loading = False
        searches.active = len(searches.objects) - 1
    update_time("time to load sidebar: ")
    

def change_language(event=None):
    global LOCALE
    LOCALE = "fr" if (LOCALE == "en") else "en"
    w_title.object = f'''<div class="title">{app_title[LOCALE]}</div>'''
    w_open_modal.name = w_about_name[LOCALE]
    w_language.name = "English" if LOCALE == "fr" else "Français"
    w_sidetitle.object = {"en":"##Start a new search","fr":"##Débuter une nouvelle recherche"}[LOCALE]
    searches.clear()
    searches.append(get_helppage(LOCALE))
    searches.closablelist[0] = False
    searches.active = 0
    update_handled(language=LOCALE)
    
w_language.on_click(change_language)

def close_modal_set_english(event):
    global LOCALE
    dash.close_modal()
    if LOCALE == 'fr':
        change_language(event)

def close_modal_set_french(event):
    global LOCALE
    dash.close_modal()
    if LOCALE == 'en':
        change_language(event)

w_enter_en.on_click(close_modal_set_english)
w_enter_fr.on_click(close_modal_set_french)

# attempt at syncable queryparam... not worth doing since LOCALE is not a param.
# TODO: create a class for LOCALE to make it a param, so this is syncable.
# import param
#class QueryParams(param.Parameterized):
#    lang = param.String('en')
#    
#    def __init__(self):
#        super().__init__()
#        qd = pn.state.location.query_params
#        print(qd)
#        if ('lang' in qd) and (qd['lang'] in ['en','fr']):
#            self.lang = qd['lang']
#        
#            
#    @param.depends('lang',watch=True)
#    def set_lang(self):
#        print(self.lang)
#        
#        global LOCALE
#        if (LOCALE != self.lang) and (self.lang in ['en','fr']):
#            change_language()
#
#queries = QueryParams()
#pn.state.location.sync(queries)
#pn.state.location.reload = False
#
    


# https://pavics.ouranos.ca/jupyter/user-redirect/proxy/9094/Dashboard
# 

# In[ ]:


pn.state.onload(update_handled)
update_time("time to serve: ")


# To use this dashboard from within PAVICS and have it run in your user account use the first line of the next cell (`s = dash.show(...)`) and comment the second one (`dash.servable()`). In that case, if you want to update the dashboard after making changes, don't forget to run `s.stop()` before rerunning  `s = dash.show(...)`.

# In[ ]:


# s = dash.show(port=9093, websocket_origin='*')
dash.servable()
# print(f"The line above is lying to you. The _real_ adress is:\n https://pavics.ouranos.ca/jupyter/user-redirect/proxy/{s.port}/")


# -*- coding: UTF-8 -*-

from django.conf.urls import patterns, url

MAIN_ENTITY_LEVEL = 'pais'
MAIN_ENTITY_NAME = 'España'

BUDGET_LOADER = 'PGEBudgetLoader'

FEATURED_PROGRAMMES = ['323M', '143A', '924M']

# Cotizaciones sociales, Sobre la Renta, IVA, Consumos específicos
OVERVIEW_INCOME_NODES = ['12', ['10', '100'], ['10', '101'], '21', '22']
# Pensiones, Transferencias a otras administraciones, Deuda pública, Desempleo, Agricultura
OVERVIEW_EXPENSE_NODES = ['21', '94', '95', '25', '41']

# Show an extra tab with institutional breakdown. Default: True.
# SHOW_INSTITUTIONAL_TAB = True

# Show an extra tab with funding breakdown (only applicable to some budgets). Default: False.
# SHOW_FUNDING_TAB = False

# Show an extra column with actual revenues/expenses. Default: True.
# Warning: the execution data still gets shown in the summary chart and in downloads.
SHOW_ACTUAL = False

# Search in entity names. Default: True.
SEARCH_ENTITIES = False

# We can define additional URLs applicable only to the theme. These will get added
# to the project URL patterns list. 
EXTRA_URLS = patterns('presupuesto-pge.views',
    url(r'^ccaa/$', 'ccaa'),      # Trailing slash optional for backwards compatibility with DVMI 1.0,
                                  # although not consistent with the rest of the site :/

    # For now at least, each article needs its own separate URL here
    url(r'^visita_guiada$', 'visita_guiada'),
    url(r'^metodologia$', 'metodologia'),
    url(r'^ojo_con_esto$', 'ojo_con_esto')
)

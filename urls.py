from django.conf.urls import url

# We can't import the theme module directly because it has a hyphen in its name. This works well.
import importlib
theme_views = importlib.import_module('presupuesto-pge.views')

# We can define additional URLs applicable only to the theme. These will get added
# to the project URL patterns list.
EXTRA_URLS = (
    url(r'^ccaa/?$', theme_views.ccaa, name='ccaa'),
    url(r'^visita_guiada$', theme_views.visita_guiada, name='visita_guiada'),
    url(r'^metodologia$', theme_views.metodologia, name='metodologia'),
    url(r'^ojo_con_esto$', theme_views.ojo_con_esto, name='ojo_con_esto')
)

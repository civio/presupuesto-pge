from django.conf.urls import url

# We can define additional URLs applicable only to the theme. These will get added
# to the project URL patterns list.
EXTRA_URLS = (
    url(r'^ccaa/?$', 'ccaa', name='ccaa'),
    url(r'^visita_guiada$', 'visita_guiada', name='visita_guiada'),
    url(r'^metodologia$', 'metodologia', name='metodologia'),
    url(r'^ojo_con_esto$', 'ojo_con_esto', name='ojo_con_esto')
)

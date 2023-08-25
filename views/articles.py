# -*- coding: UTF-8 -*-

from budget_app.views.helpers import *

def visita_guiada(request):
    c = get_context(request, css_class='body-articles', title=u'Visita Guiada')

    return render_response('articles/visita_guiada.html', c)


def metodologia(request):
    c = get_context(request, css_class='body-articles', title=u'Metodología')

    return render_response('articles/metodologia.html', c)


def ojo_con_esto(request):
    c = get_context(request, css_class='body-articles', title=u'Ojo con esto')

    return render_response('articles/ojo_con_esto.html', c)

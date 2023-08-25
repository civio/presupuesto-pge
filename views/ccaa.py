# -*- coding: UTF-8 -*-

from budget_app.views.helpers import *

def ccaa(request):
    c = get_context(request, css_class='body-ccaa', title=u'Comunidades Autónomas')

    return render_response('ccaa/index.html', c)

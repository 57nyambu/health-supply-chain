from django.shortcuts import render

def pos(request):
    """
    Render the Point of Sale (POS) interface.
    """
    return render(request, 'sales/pos.html', {
        'title': 'Point of Sale',
        'page_title': 'POS Interface',
        'page_description': 'Manage sales transactions efficiently.',
    })
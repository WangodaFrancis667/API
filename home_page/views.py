from django.shortcuts import render
from datetime import datetime

def root_page(request):
    data = {
        "year": datetime.now().year,
    }

    return render(request, 'home/home.html', data)
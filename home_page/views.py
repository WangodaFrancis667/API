from django.shortcuts import render

def root_page(request):
    return render(request, 'home/home.html')
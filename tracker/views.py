from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Expense, Category

# ➕ Dashboard View
@login_required
def dashboard(request):
    # Fetch expenses of the logged-in user, most recent first
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    
    # Calculate total expense
    total_expense = sum(expense.amount for expense in expenses)
    
    # Fetch all categories
    categories = Category.objects.all()
    
    return render(request, 'tracker/dashboard.html', {
        'expenses': expenses,
        'total_expense': total_expense,
        'categories': categories,
    })

# ➕ Add Expense View
@login_required
def add_expense(request):
    if request.method == "POST":
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date = request.POST.get('date', timezone.now().date())

        # Get the category object
        category = get_object_or_404(Category, id=category_id)
        
        # Create new expense
        Expense.objects.create(
            user=request.user,
            title=title,
            amount=amount,
            category=category,
            date=date
        )
        
        return redirect('dashboard')
    
    # For GET request, show the add expense form with categories
    categories = Category.objects.all()
    return render(request, 'tracker/add_expense.html', {'categories': categories})

# ✏️ Edit Expense
@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    if request.method == "POST":
        expense.title = request.POST.get('title')
        expense.amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        expense.category = get_object_or_404(Category, id=category_id)
        expense.date = request.POST.get('date', timezone.now().date())
        expense.save()
        return redirect('dashboard')
    
    categories = Category.objects.all()
    return render(request, 'tracker/edit_expense.html', {
        'expense': expense,
        'categories': categories
    })

# ❌ Delete Expense
@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    expense.delete()
    return redirect('dashboard')

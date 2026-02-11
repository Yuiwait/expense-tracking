from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime
import json

from .models import Expense, Category, Budget


# 📊 Dashboard View
@login_required
def dashboard(request):
    # Fetch expenses of logged-in user
    expenses = Expense.objects.filter(user=request.user).order_by('-date')

    # Calculate total expense using ORM
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # Current month & year
    now = datetime.now()

    # Fetch current month's budget
    budget = Budget.objects.filter(
        user=request.user,
        month=now.month,
        year=now.year
    ).first()

    # Calculate remaining budget
    remaining = None
    if budget:
        remaining = budget.amount - total_expense

    categories = Category.objects.all()

    # 📈 Category Breakdown
    category_data = expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    category_labels = [item['category__name'] for item in category_data]
    category_amounts = [float(item['total']) for item in category_data]

    # 📊 Monthly Spending Trend (Last 12 months)
    monthly_data = {}
    
    for i in range(11, -1, -1):
        # Calculate month_date by subtracting months
        month_offset = i
        month = now.month - month_offset
        year = now.year
        
        while month <= 0:
            month += 12
            year -= 1
        
        month_key = datetime(year, month, 1).strftime('%b %Y')
        
        monthly_expenses = expenses.filter(
            date__year=year,
            date__month=month
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        monthly_data[month_key] = float(monthly_expenses)

    monthly_labels = list(monthly_data.keys())
    monthly_amounts = list(monthly_data.values())

    # 🎯 Top Categories (for summary cards)
    top_categories = []
    for category_item in category_data[:3]:
        percentage = (category_item['total'] / total_expense * 100) if total_expense > 0 else 0
        top_categories.append({
            'name': category_item['category__name'],
            'amount': category_item['total'],
            'percentage': round(percentage, 1)
        })

    return render(request, 'tracker/dashboard.html', {
        'expenses': expenses,
        'total_expense': total_expense,
        'categories': categories,
        'budget': budget,
        'remaining': remaining,
        'category_labels': json.dumps(category_labels),
        'category_amounts': json.dumps(category_amounts),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_amounts': json.dumps(monthly_amounts),
        'top_categories': top_categories,
    })


# ➕ Add Expense
@login_required
def add_expense(request):
    if request.method == "POST":
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date = request.POST.get('date') or timezone.now().date()

        category = get_object_or_404(Category, id=category_id)

        # Ensure numeric amount stored as float
        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0.0

        Expense.objects.create(
            user=request.user,
            title=title,
            amount=amount_val,
            category=category,
            date=date
        )

        return redirect('dashboard')

    categories = Category.objects.all()
    today = timezone.now().date()
    return render(request, 'tracker/add_expense.html', {
        'categories': categories,
        'today': today,
    })


# ✏️ Edit Expense
@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)

    if request.method == "POST":
        expense.title = request.POST.get('title')
        expense.amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        expense.category = get_object_or_404(Category, id=category_id)
        expense.date = request.POST.get('date') or timezone.now().date()
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


# 💰 Set / Update Monthly Budget
@login_required
def set_budget(request):
    now = datetime.now()

    if request.method == "POST":
        amount = request.POST.get('amount')
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))

        Budget.objects.update_or_create(
            user=request.user,
            month=month,
            year=year,
            defaults={'amount': float(amount)}
        )

        return redirect('dashboard')

    # For GET: provide current month's budget (if any) and helpers for the template
    budget = Budget.objects.filter(user=request.user, month=now.month, year=now.year).first()
    months = list(range(1, 13))
    current_year = now.year

    return render(request, 'tracker/set_budget.html', {
        'budget': budget,
        'months': months,
        'current_month': now.month,
        'current_year': current_year,
    })


# 📝 User Registration
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validation
        errors = []
        
        if not username or not email or not password1 or not password2:
            errors.append("All fields are required.")
        elif User.objects.filter(username=username).exists():
            errors.append("Username already taken. Please choose another.")
        elif User.objects.filter(email=email).exists():
            errors.append("Email already registered.")
        elif len(password1) < 8:
            errors.append("Password must be at least 8 characters long.")
        elif password1 != password2:
            errors.append("Passwords do not match.")
        elif password1.isdigit():
            errors.append("Password cannot be entirely numeric.")
        else:
            # Create and login user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )
            
            # Auto-login
            user = authenticate(username=username, password=password1)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
        
        # Return with errors
        return render(request, 'registration/register.html', {
            'form': {
                'username': {'value': username, 'errors': []},
                'email': {'value': email, 'errors': []},
            },
            'form_errors': errors
        })
    
    return render(request, 'registration/register.html', {'form': {}})

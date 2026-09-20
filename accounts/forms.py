from django import forms
from django.contrib.auth import authenticate
from .models import User

class RegisterForm(forms.ModelForm):
    password = forms.CharField(label='Mật khẩu', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu ít nhất 6 ký tự'}))
    password_confirm = forms.CharField(label='Xác nhận mật khẩu', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu'}))

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'phone', 'address', 'gender', 'date_of_birth']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên đăng nhập'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Họ và tên đầy đủ'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Địa chỉ email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại liên hệ'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Địa chỉ thường trú'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Mật khẩu xác nhận không khớp!')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'patient'  # Đăng ký mặc định là bệnh nhân
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(label='Tên đăng nhập', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên đăng nhập'}))
    password = forms.CharField(label='Mật khẩu', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mật khẩu'}))

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError('Tên đăng nhập hoặc mật khẩu không chính xác!')
            self.user_cache = user
        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'address', 'gender', 'date_of_birth']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

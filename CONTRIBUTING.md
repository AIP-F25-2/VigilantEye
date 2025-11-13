# Contributing to VIGILANTEye

Thank you for your interest in contributing to VIGILANTEye! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

1. **Fork the Repository**
   - Visit [https://github.com/AIP-F25-2/VigilantEye](https://github.com/AIP-F25-2/VigilantEye)
   - Click the "Fork" button to create your own copy

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/VigilantEye.git
   cd VigilantEye
   ```

3. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📝 Development Guidelines

### Code Style
- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Reference issue numbers if applicable

Example:
```
Add face detection API endpoint
Fix authentication token expiration issue
Update dashboard UI with new design
```

### Testing
- Write tests for new features
- Ensure all tests pass before submitting
- Test your changes locally

## 🔄 Pull Request Process

1. **Update Your Branch**
   ```bash
   git checkout dev
   git pull upstream dev
   git checkout feature/your-feature-name
   git rebase dev
   ```

2. **Test Your Changes**
   - Run the application locally
   - Test all affected features
   - Check for any errors or warnings

3. **Submit Pull Request**
   - Push your branch to your fork
   - Create a pull request to the `dev` branch
   - Provide a clear description of your changes
   - Reference any related issues

## 🐛 Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Screenshots if applicable

## 📋 Code Review

- All pull requests require review
- Address review comments promptly
- Be open to feedback and suggestions

## 🎯 Areas for Contribution

- Bug fixes
- New features
- Documentation improvements
- Performance optimizations
- UI/UX enhancements
- Test coverage
- Code refactoring

## 📞 Questions?

Feel free to open an issue for questions or reach out to the maintainers.

Thank you for contributing to VIGILANTEye! 🎉


# 👥 VIGILANTEye Collaboration Guide

This guide helps team members collaborate effectively on the VIGILANTEye project.

## 🔗 Repository Information

- **GitHub Repository**: [https://github.com/AIP-F25-2/VigilantEye](https://github.com/AIP-F25-2/VigilantEye)
- **Main Branch**: `main` (production)
- **Development Branch**: `dev` (development)
- **Default Branch**: `dev`

## 👨‍💻 Team Members

- [@Sukhjitsingh2](https://github.com/Sukhjitsingh2) - sukhjit singh
- [@NSriDatta16](https://github.com/NSriDatta16) - N SriDatta
- [@probablybhavik](https://github.com/probablybhavik) - Bhavik Gandhi
- [@sameerkeshvani](https://github.com/sameerkeshvani)

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/AIP-F25-2/VigilantEye.git
cd VigilantEye
git checkout dev
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file (not committed to Git):

```bash
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/flaskapi
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret
```

### 4. Set Up Database

```bash
flask db upgrade
```

## 🔀 Git Workflow

### Branch Strategy

- **`main`**: Production-ready code (protected)
- **`dev`**: Development branch (default)
- **Feature branches**: `feature/feature-name`
- **Bug fix branches**: `fix/bug-description`

### Working on Features

1. **Create a feature branch**:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code
   - Test locally
   - Commit frequently with clear messages

3. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add: Description of your changes"
   ```

4. **Push to GitHub**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**:
   - Go to GitHub repository
   - Click "New Pull Request"
   - Select `dev` as base branch
   - Add description and reviewers
   - Wait for review and approval

6. **After PR is merged**:
   ```bash
   git checkout dev
   git pull origin dev
   git branch -d feature/your-feature-name  # Delete local branch
   ```

## 📝 Commit Message Guidelines

Use clear, descriptive commit messages:

**Format**: `Type: Brief description`

**Types**:
- `Add:` - New feature
- `Fix:` - Bug fix
- `Update:` - Update existing feature
- `Remove:` - Remove feature
- `Refactor:` - Code refactoring
- `Docs:` - Documentation changes
- `Style:` - Code style changes
- `Test:` - Test additions/changes

**Examples**:
```
Add: Face detection API endpoint
Fix: Authentication token expiration issue
Update: Dashboard UI with new design
Docs: Update README with deployment instructions
```

## 🔍 Code Review Process

1. **Before submitting PR**:
   - Ensure code follows project style
   - Run tests locally
   - Update documentation if needed
   - Check for linting errors

2. **PR Requirements**:
   - Clear description of changes
   - Reference related issues
   - Screenshots for UI changes
   - Test results

3. **Review Checklist**:
   - [ ] Code follows style guidelines
   - [ ] Tests pass
   - [ ] Documentation updated
   - [ ] No breaking changes (or documented)
   - [ ] Security considerations addressed

## 🏗️ Project Structure

```
VIGILANTEye/
├── app/
│   ├── controllers/      # API and web controllers
│   ├── models/          # Database models
│   ├── schemas/         # Marshmallow schemas
│   ├── services/        # Business logic
│   ├── templates/       # HTML templates
│   ├── static/          # CSS, JS, images
│   └── utils/           # Utility functions
├── migrations/          # Database migrations
├── .github/workflows/   # CI/CD pipelines
└── [config files]
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app tests/
```

### Writing Tests

- Place tests in `tests/` directory
- Follow naming: `test_*.py`
- Use descriptive test names
- Test both success and failure cases

## 🔧 Development Tools

### Code Quality

```bash
# Format code
black app/

# Check style
flake8 app/

# Type checking (if using mypy)
mypy app/
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

## 📋 Issue Management

### Creating Issues

Use GitHub Issues for:
- Bug reports
- Feature requests
- Documentation improvements
- Questions

**Issue Template**:
- Clear title
- Description
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details

### Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `question` - Further information needed
- `help wanted` - Extra attention needed

## 🚢 Deployment

### Automated Deployment

- **CI/CD**: GitHub Actions automatically deploy on push to `main`
- **Staging**: Deploy to `dev` branch for testing
- **Production**: Deploy to `main` branch

### Manual Deployment

See `deploy-manual.ps1` for step-by-step instructions.

## 💬 Communication

### GitHub Discussions

Use GitHub Discussions for:
- General questions
- Feature ideas
- Best practices
- Team coordination

### Pull Request Comments

- Be constructive and respectful
- Ask questions if something is unclear
- Suggest improvements
- Approve when satisfied

## 🔐 Security

- **Never commit secrets** (tokens, passwords, keys)
- Use environment variables for sensitive data
- Review security implications of changes
- Report security issues privately

## 📚 Resources

- [README.md](README.md) - Main documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Project overview
- [FACEAI_INTEGRATION_GUIDE.md](FACEAI_INTEGRATION_GUIDE.md) - FaceAI setup

## 🆘 Getting Help

1. Check documentation first
2. Search existing issues
3. Ask in GitHub Discussions
4. Create an issue if needed
5. Contact team members

## ✅ Best Practices

1. **Pull before push**: Always pull latest changes before pushing
2. **Small commits**: Make frequent, small commits
3. **Test locally**: Test your changes before pushing
4. **Update docs**: Keep documentation up to date
5. **Communicate**: Let team know about major changes
6. **Review code**: Review your own code before PR
7. **Be responsive**: Respond to PR comments promptly

---

**Happy Collaborating! 🎉**

For questions or issues, please open a GitHub Issue or Discussion.


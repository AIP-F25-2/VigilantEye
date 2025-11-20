# 🔀 Git Workflow Guide for VIGILANTEye

## Branch Strategy

### Main Branches
- **`main`**: Production-ready code (protected)
- **`dev`**: Development branch (all features merged here)

### Feature Branches
- **`feature/feature-name`**: New features
- **`fix/bug-name`**: Bug fixes
- **`refactor/component-name`**: Code refactoring

---

## 📋 Workflow Steps

### 1. Before Starting Work

```bash
# Ensure you're on dev branch
git checkout dev

# Pull latest changes
git pull origin dev

# Create a new feature branch
git checkout -b feature/your-feature-name
# OR for fixes:
git checkout -b fix/your-fix-name
```

### 2. Making Changes

```bash
# Make your code changes
# ... edit files ...

# Stage your changes
git add .

# Or stage specific files
git add app/controllers/your_file.py
git add testcase/test_your_file.py
```

### 3. Committing Changes

```bash
# Write a clear commit message
git commit -m "feat: Add user authentication endpoint

- Implement login endpoint
- Add JWT token generation
- Add unit tests for authentication
- Fix security issues in test credentials

Fixes: #123"

# Commit message format:
# <type>: <subject>
#
# <body>
#
# <footer>
```

### 4. Commit Message Types

- **`feat`**: New feature
- **`fix`**: Bug fix
- **`refactor`**: Code refactoring
- **`docs`**: Documentation changes
- **`test`**: Adding/updating tests
- **`chore`**: Maintenance tasks
- **`security`**: Security fixes
- **`perf`**: Performance improvements

### 5. Pushing to Remote

```bash
# Push your branch to remote
git push origin feature/your-feature-name

# If branch doesn't exist remotely:
git push -u origin feature/your-feature-name
```

### 6. Creating Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select: `dev` ← `feature/your-feature-name`
4. Fill in PR description:
   ```
   ## Description
   Brief description of changes
   
   ## Changes Made
   - Change 1
   - Change 2
   - Change 3
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   
   ## Screenshots
   [Add screenshots if UI changes]
   
   ## Related Issues
   Fixes #123
   ```

---

## 📸 Git Commit Screenshots Guide

### What to Screenshot

1. **Terminal/Command Line**
   - Show `git status` before commit
   - Show `git commit` command
   - Show `git push` command
   - Show successful push confirmation

2. **GitHub Interface**
   - Show commit in GitHub
   - Show branch comparison
   - Show PR creation

### Example Screenshot Workflow

#### Step 1: Show Your Changes
```bash
git status
# Screenshot this
```

#### Step 2: Show Commit
```bash
git commit -m "feat: Add new feature"
# Screenshot the commit message and confirmation
```

#### Step 3: Show Push
```bash
git push origin dev
# Screenshot the push output
```

#### Step 4: Show GitHub
- Screenshot the commit on GitHub
- Screenshot the branch view
- Screenshot the PR (if applicable)

---

## 🖼️ Screenshot Examples

### Good Screenshot Includes:
- ✅ Clear terminal output
- ✅ Commit hash visible
- ✅ Branch name visible
- ✅ File changes visible
- ✅ Timestamp (if possible)

### Bad Screenshot:
- ❌ Blurry text
- ❌ Cut off output
- ❌ Missing context

---

## 🔄 Daily Workflow

### Morning Routine
```bash
# 1. Checkout dev
git checkout dev

# 2. Pull latest
git pull origin dev

# 3. Check status
git status

# 4. Create feature branch
git checkout -b feature/today-feature
```

### During Development
```bash
# Make changes, then:
git add .
git commit -m "feat: Description"
git push origin feature/today-feature
```

### End of Day
```bash
# Push all work
git push origin feature/today-feature

# Create PR if ready
# OR leave branch for next day
```

---

## 🚨 Common Issues & Solutions

### Issue: "Your branch is behind"
```bash
# Update your branch
git checkout dev
git pull origin dev
git checkout feature/your-branch
git merge dev
# OR
git rebase dev
```

### Issue: Merge Conflicts
```bash
# Resolve conflicts in files
# Then:
git add .
git commit -m "fix: Resolve merge conflicts"
git push origin feature/your-branch
```

### Issue: Wrong Branch
```bash
# Stash changes
git stash

# Switch branch
git checkout correct-branch

# Apply changes
git stash pop
```

---

## ✅ Pre-Push Checklist

Before pushing to `dev`:

- [ ] All tests pass locally
- [ ] Code follows style guidelines
- [ ] No hardcoded credentials
- [ ] Commit messages are clear
- [ ] Related issues are referenced
- [ ] Documentation updated (if needed)
- [ ] Screenshots taken (if requested)

---

## 📝 Commit Message Template

```
<type>: <short summary>

<detailed description>

<footer with issue references>
```

### Example:
```
feat: Add face detection API endpoint

- Implement POST /api/faceai/detect endpoint
- Add face detection service integration
- Add unit tests for face detection
- Update API documentation

Fixes: #45
Related: #23
```

---

## 🎯 Best Practices

1. **Commit Often**: Small, logical commits
2. **Clear Messages**: Describe what and why
3. **Test Before Push**: Run tests locally
4. **Review Your Code**: Check diffs before committing
5. **Keep Branches Clean**: Delete merged branches
6. **Sync Regularly**: Pull from dev frequently
7. **Document Changes**: Update README/docs if needed

---

## 📞 Need Help?

- Check [Git Documentation](https://git-scm.com/doc)
- Review [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- Ask in team chat
- Review existing PRs for examples

---

## 🔗 Quick Reference

```bash
# Status
git status

# Log
git log --oneline -10

# Diff
git diff

# Branch list
git branch -a

# Remote info
git remote -v

# Stash
git stash
git stash pop

# Reset (careful!)
git reset --soft HEAD~1  # Undo last commit, keep changes
```

---

**Remember**: Always work on feature branches, never directly on `dev` or `main`!


# Template Reorganization Summary

## Overview
Templates have been reorganized by role to improve maintainability and clarity.

## New Folder Structure

```
src/web/templates/
├── admin/           # Admin-only templates
│   ├── _sidebar_admin.html
│   ├── admin_dashboard.html
│   ├── clients.html
│   ├── edit_user.html
│   ├── new_client.html
│   ├── new_user.html
│   └── users.html
├── common/          # Shared templates
│   ├── 404.html
│   ├── 500.html
│   ├── _base.html
│   ├── index.html
│   └── login.html
└── user/            # User templates (for operators, managers, regular users)
    ├── _sidebar_user.html
    └── user_dashboard.html
```

## Code Changes Made

### 1. Python Files Updated
- `src/web/main.py`: Updated template paths for login, dashboards, and error pages
- `src/web/routers/users.py`: Updated template paths for user management pages
- `src/web/routers/clients.py`: Updated template paths for client management pages

### 2. Template Files Updated
- All admin templates now extend `../common/_base.html`
- All user templates now extend `../common/_base.html`
- Common templates (404.html, 500.html) extend `_base.html` (same directory)
- `_base.html` includes updated to reference:
  - `admin/_sidebar_admin.html` for admin users
  - `user/_sidebar_user.html` for other users

## Benefits
1. **Clear role separation**: Easy to identify which templates are for which user type
2. **Better security**: Admin templates are clearly separated from user templates
3. **Easier maintenance**: Templates are organized logically by their access level
4. **Scalability**: Easy to add new role-specific templates in the future
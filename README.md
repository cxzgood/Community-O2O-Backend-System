# Community O2O Backend System

一个基于 Flask + SQLAlchemy 的轻量级社区便民服务后端系统。

## 项目概览
本项目实现了社区本地生活服务的线上线下闭环（O2O），涵盖前端居民服务预约（维修、家政、餐饮）与后台管理员的工单调度、状态机流转及细粒度权限管控。

## 核心技术栈
- 后端框架：Python 3.x, Flask (RESTful 路由)
- 数据库与 ORM：MySQL, Flask-SQLAlchemy, PyMySQL
- 鉴权与安全：Flask-Session, Werkzeug (PBKDF2 加密)
- 前端渲染：Jinja2, Bootstrap 5

## 核心工程实现
1. 业务数据闭环：打通多端数据流转，从前端表单提交、后端 ORM 持久化，至后台大屏的接单与状态归档。
2. 权限与安全机制：后台敏感路由采用全局请求拦截器（@app.before_request）校验 Session 状态。拒绝明文密码，数据库采用加盐哈希（Hash & Salt）算法持久化管理员凭证。
3. 亿级数据量防备与查询优化：针对后台海量工单场景，弃用单次全表扫描，基于 SQLAlchemy 引擎实现了按业务状态过滤（Filter）与数据分页（Pagination）。
4. 工程化部署：使用 `python-dotenv` 隔离敏感配置，支持 `init_db()` 钩子在项目启动时自动探测并初始化表结构及默认高权限账户。

## 本地运行指南

1. 安装依赖
```bash
pip install -r requirements.txt

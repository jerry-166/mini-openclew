---
name: docker-desktop_windows_operation_guide
description: 提供在 Windows 环境下使用 Docker Desktop 的常用操作指南，包括管理容器自启动和使用 Docker Compose。
---

# Docker Desktop for Windows 操作指南

## 1. 功能说明
此技能作为一个内部知识库，用于指导如何在 Windows 环境下使用 `terminal` 工具执行常见的 Docker Desktop 操作。主要涵盖：
- **管理容器自启动**：检查哪些容器会自动重启，以及如何更新它们的重启策略。
- **使用 Docker Compose**：通过 `docker-compose.yml` 文件启动和停止多容器应用。

## 2. 使用步骤

### 2.1 管理容器自启动

#### A. 查看自启动容器
在 **PowerShell** 中运行以下脚本，可以列出所有设置为自启动的容器及其策略。

```powershell
docker ps -a -q | ForEach-Object {
    $restart = docker inspect $_ --format='{{.HostConfig.RestartPolicy.Name}}'
    if ($restart -ne "no") {
        $name = docker inspect $_ --format='{{.Name}}' | ForEach-Object { $_ -replace '^/' }
        Write-Host "$name : $restart"
    }
}
```

#### B. 更新启动策略
使用 `docker update` 命令修改容器的重启策略。

- **设置为总是自启动**:
  ```shell
  docker update --restart=always <容器名或容器ID>
  ```

- **取消自启动**:
  ```shell
  docker update --restart=no <容器名或容器ID>
  ```

### 2.2 使用 Docker Compose

在 `docker-compose.yml` 文件所在的目录中执行以下命令。

- **启动并构建服务 (后台模式)**:
  ```shell
  docker compose up -d
  ```

- **停止并移除服务**:
  ```shell
  docker compose down
  ```

## 3. 注意事项
- 执行脚本和命令时，应使用 `terminal` 工具。
- 上述 PowerShell 脚本是为 Windows 环境设计的。
- `docker compose` 命令需要确保已安装 Docker Desktop 且当前目录正确。

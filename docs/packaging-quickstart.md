# 打包快速开始

## 一键打包

### Windows
```cmd
build\build-windows.bat
```

### Linux
```bash
./build/build-linux.sh
```

### macOS
```bash
./build/build-macos.sh
```

## 输出位置

打包完成后，可执行文件位于：
- Windows: `dist\hou-cli.exe`
- Linux/macOS: `dist/hou-cli`

发布包位于：
- Windows: `dist\hou-cli-windows-release\`
- Linux: `dist\hou-cli-linux-release\`
- macOS: `dist\hou-cli-macos-release\`

## 测试打包结果

```bash
# 测试帮助命令
./dist/hou-cli --help

# 测试聊天功能
./dist/hou-cli chat "Hello"
```

## 创建压缩包

### Windows
```powershell
Compress-Archive -Path dist\hou-cli-windows-release\* -DestinationPath dist\hou-cli-windows-amd64.zip
```

### Linux/macOS
```bash
cd dist/hou-cli-linux-release  # 或 hou-cli-macos-release
tar -czf ../hou-cli-linux-amd64.tar.gz *
```

## 更多信息

- 详细文档: [PACKAGING.md](PACKAGING.md)
- 发布指南: [RELEASE.md](../../RELEASE.md)


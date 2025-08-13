# HaiLin Climate Integration for Home Assistant

**本插件是根据妖神的插件改编而来 [https://github.com/Yonsm/ZhiSaswell](https://github.com/Yonsm/ZhiSaswell) ，非常感谢妖神**

Hailin 地暖温控面板插件，我家里用的是 **㻏动** 这一款。

当前已知支持的设备：

* 㻏动  
   * devType 8  
   * devType 9 （需要配置support参数，见下文）
* 绿动  
   * devType 14

相关使用方式都是基于以上两款设备。其他型号就不太确定是否能用，欢迎抓包后提issue给我

## 🚀 新版本特性 (v2.0.0)

### ✨ 架构重构
- **模块化设计**: 将代码重构为多个独立模块，提高可维护性
- **配置条目支持**: 支持通过Home Assistant UI进行配置，无需编辑YAML文件
- **改进的认证系统**: 独立的认证模块，更好的错误处理和会话管理
- **统一资源管理**: 自动管理HTTP会话和资源清理

### 🔧 技术改进
- **职责分离**: 认证、配置管理、实体逻辑分别独立
- **错误处理**: 更详细的日志记录和异常处理
- **性能优化**: 减少HTTP会话创建，优化内存使用
- **类型注解**: 添加更多类型注解，提高代码质量

## 📋 安装准备

### 方法一：手动安装
把 `hailin` 文件夹放入 `custom_components` 目录

### 方法二：HACS安装
在 HACS 中添加自定义库的方式安装

## ⚙️ 配置方法

通过Home Assistant UI进行配置：

1. 打开Home Assistant
2. 进入"设置" → "设备和服务" → "添加集成"
3. 搜索"HaiLin"
4. 按照向导完成配置

## 📱 使用方式

HA面板会根据设备型号以及当前所处模式变化。

比如送风模式时无法调节温度，制热（地暖）模式时无法调节风速。

## ⚠️ 重要注意事项

### 设备分组要求
请确保APP的分组管理中至少存在一个分组并且所有设备都在分组中。否则会出现接口无法找到该设备的情况。

### 版本兼容性
- **Home Assistant**: 新版本基于2025.8.0开发

## 🔄 从旧版本迁移

### Breaking Changes
**配置方式变更**: 不再支持YAML配置，必须通过UI配置

### 迁移步骤
1. 删除旧的YAML配置
2. 通过UI重新配置集成
3. 验证设备功能正常

## 🐛 故障排除

### 常见问题
1. **设备未找到**: 检查APP中的设备分组设置
2. **认证失败**: 验证用户名密码和登录类型
3. **功能异常**: 检查设备型号是否在支持列表中

### 调试模式
启用调试日志：
```yaml
logger:
  custom_components.hailin: debug
```

## 📚 参考链接

* [原始项目](https://github.com/alkalixin/Hailin-Climate)
* [妖神插件](https://github.com/Yonsm/ZhiSaswell)
* [Home Assistant论坛讨论](https://bbs.hassbian.com/thread-3387-1-1.html)

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

本项目基于原始项目开发，遵循相同的许可证。

---

**注意**: 这是一个重大版本更新，包含了架构重构和Breaking Changes。建议在生产环境升级前先在测试环境中验证功能。
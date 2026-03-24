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

## 🆕 v2.0.1 修复说明

### ✅ 稳定性修复
- **自动处理登录过期**: 请求返回 `401` 时会自动重新登录并重试一次
- **保留缓存设备状态**: 云端短暂异常时不再清空设备列表，避免实体直接报错
- **修复实体越界异常**: 解决 `IndexError: list index out of range` 导致的状态写回失败
- **网络异常自动重试**: 请求发生连接重置等瞬时错误时会自动重试一次
- **优化定时任务清理**: 修复定时登录回调签名和卸载时监听清理问题

### 🎯 重点解决的问题
- 设备最新状态长时间不刷新
- Home Assistant 中无法控制设备
- 日志反复出现 `登录超时，请重新登录`
- 日志反复出现 `Failed to get device list from house`
- 日志出现 `Cannot connect to host yunpan.hailin.com:443`

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
4. **状态不更新 / 无法控制**:
   - 升级到 `v2.0.1` 或更新后的代码
   - 检查日志中是否存在 `401`、`登录超时，请重新登录`
   - 检查日志中是否存在 `Cannot connect to host yunpan.hailin.com:443`
   - 确认海林 APP 中设备仍在房屋分组内
   - 在 HA 中重载集成或重启后再次观察

### 推荐排查顺序
1. 先查看是否有 `401` / `登录超时`，如果有，优先排查账号登录状态
2. 再查看是否有 `Cannot connect to host yunpan.hailin.com:443`，如果有，优先排查 HA 宿主机网络、DNS、代理
3. 如果是 `Failed to get device list from house`，优先检查海林 APP 的房屋和分组是否正常
4. 打开调试日志后观察一次完整刷新周期，确认是否已经自动重登并恢复设备列表

### 调试模式
启用调试日志：
```yaml
logger:
  logs:
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

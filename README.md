# [https://github.com/alkalixin/Hailin-Climate](https://github.com/alkalixin/Hailin-Climate)

**本插件是根据妖神的插件改编而来 [https://github.com/Yonsm/ZhiSaswell](https://github.com/Yonsm/ZhiSaswell) ，非常感谢妖神**

[Hailin](https://www.hailin.com/html/PC/index.html) 地暖温控面板插件，我家里用的是 [**㻏动**](https://www.hailin.com/html/PC/proDetail.html?id=106) 这一款。

当前已知支持的设备：
* [㻏动](https://www.hailin.com/html/PC/proDetail.html?id=106)
  * devType 8
  * devType 9 （需要配置support参数，见下文）
* [绿动](https://www.hailin.com/html/PC/proDetail.html?id=121)
  * devType 14

相关使用方式都是基于以上两款设备。其他型号就不太确定是否能用，欢迎抓包后提issue给我

## 1. 安装准备

把 `hailin` 放入 `custom_components`；也支持在 [HACS](https://hacs.xyz/) 中添加自定义库的方式安装。

## 2. 配置方法

```
climate:
  - platform: hailin
    #type: mail
    type: mobile
    username: ********
    password: ********
    # scan_interval: 300
    # temp_step: 1
    # support_fan: true
    # support_cool: false
    # support_heat: true
```

`scan_interval` 可以自行调整状态拉取时间间隔秒数，默认五分钟同步一次温度和状态，是不是慢了点儿，不过地暖本来就很慢：）

`temp_step` 每次点击加减温度时的温度跨度，默认值为0.5，可以根据实际情况修改。例如目前我的㻏动面板在app中以及HA中已经无法以0.5为单位加减温度了

`support_XXX` 这三个选填参数可以`全局`指定所有面板支持的模式。当你的设备不在已知支持设备列表，并且默认状态下没有正确读出所有模式时可以使用这三个参数手动指定模式。

## 3. 使用方式
HA面板会根据设备型号以及当前所处模式变化。

比如送风模式时无法调节温度，制热（地暖）模式时无法调节风速。
![㻏动](https://s4.ax1x.com/2022/01/04/TLJ2ct.jpg)
![绿动](https://s4.ax1x.com/2022/01/04/TLJRjP.jpg)
![绿动](https://s4.ax1x.com/2022/01/04/TLJfnf.jpg)
![绿动](https://s4.ax1x.com/2022/01/04/TLJg1I.jpg)


## 4. 注意
请确保APP的分组管理中至少存在一个分组并且所有设备都在分组中。否则会出现接口无法找到该设备的情况

[![分组示例](https://s1.ax1x.com/2022/06/08/XrVT3D.jpg)](https://imgtu.com/i/XrVT3D)

## 5. 参考

- [https://github.com/Yonsm/ZhiSaswell](https://github.com/Yonsm/ZhiSaswell)
- [https://bbs.hassbian.com/thread-3387-1-1.html](https://bbs.hassbian.com/thread-3387-1-1.html)

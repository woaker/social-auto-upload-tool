# 使用Cursor进行Java开发的指南与优化建议

> 📎 **原文链接**: [https://juejin.cn/post/7469611433765388340](https://juejin.cn/post/7469611433765388340)
> ⏰ **转发时间**: 2025-06-15 22:22

---

.markdown-body{color:#595959;font-size:15px;font-family:-apple-system,system-ui,BlinkMacSystemFont,Helvetica Neue,PingFang SC,Hiragino Sans GB,Microsoft YaHei,Arial,sans-serif;background-image:linear-gradient(90deg,rgba(60,10,30,.04) 3%,transparent 0),linear-gradient(1turn,rgba(60,10,30,.04) 3%,transparent 0);background-size:20px 20px;background-position:50%}.markdown-body p{color:#595959;font-size:15px;line-height:2;font-weight:400}.markdown-body p+p{margin-top:16px}.markdown-body h1,.markdown-body h2,.markdown-body h3,.markdown-body h4,.markdown-body h5,.markdown-body h6{padding:30px 0;margin:0;color:#135ce0}.markdown-body h1{position:relative;text-align:center;font-size:22px;margin:50px 0}.markdown-body h1:before{position:absolute;content:"";top:-10px;left:50%;width:32px;height:32px;transform:translateX(-50%);background-size:100% 100%;opacity:.36;background-repeat:no-repeat;background:url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAABfVBMVEX///8Ad/8AgP8AgP8AgP8Aff8AgP8Af/8AgP8AVf8Af/8Af/8AgP8AgP8Af/8Afv8AAP8Afv8Afv8Aef8AgP8AdP8Afv8AgP8AgP8Acf8Ae/8AgP8Af/8AgP8Af/8Af/8AfP8Afv8AgP8Af/8Af/8Afv8Afv8AgP8Afv8AgP8Af/8Af/8AgP8AgP8Afv8AgP8Af/8AgP8AgP8AgP8Ae/8Afv8Af/8AgP8Af/8AgP8Af/8Af/8Aff8Af/8Abf8AgP8Af/8AgP8Af/8Af/8Afv8AgP8AgP8Afv8Afv8AgP8Af/8Aff8AgP8Afv8AgP8Aff8AgP8AfP8AgP8Ae/8AgP8Af/8AgP8AgP8AgP8Afv8AgP8AgP8AgP8Afv8AgP8AgP8AgP8AgP8AgP8Af/8AgP8Af/8Af/8Aev8Af/8AgP8Aff8Afv8AgP8AgP8AgP8Af/8AgP8Af/8Af/8AgP8Afv8AgP8AgP8AgP8AgP8Af/8AeP8Af/8Af/8Af//////rzEHnAAAAfXRSTlMAD7CCAivatxIDx5EMrP19AXdLEwgLR+6iCR/M0yLRzyFF7JupSXn8cw6v60Q0QeqzKtgeG237HMne850/6Qeq7QaZ+WdydHtj+OM3qENCMRYl1B3K2U7wnlWE/mhlirjkODa9FN/BF7/iNV/2kASNZpX1Wlf03C4stRGxgUPclqoAAAABYktHRACIBR1IAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH4gEaBzgZ4yeM3AAAAT9JREFUOMvNUldbwkAQvCAqsSBoABE7asSOBRUVVBQNNuy9996789+9cMFAMHnVebmdm+/bmdtbQv4dOFOW2UjPzgFyLfo6nweKfIMOBYWwFtmMPGz2Yj2pJI0JDq3udJW6VVbmKa9I192VQFV1ktXUAl5NB0cd4KpnORqsEO2ZIRpF9gJfE9Dckqq0KuZt7UAH5+8EPF3spjsRpCeQNO/tA/qDwIDA+OCQbBoKA8NOdjMySgcZGVM6jwcgRuUiSs0nlPFNSrEpJfU0jTLD6llqbvKxei7OzvkFNQohi0vAsj81+MoqsCaoPOQFgus/1LyxichW+hS2JWCHZ7VlF9jb187pIAYcHiViHAMnp5mTjJ8B5xeEXF4B1ze/fTh/C0h398DDI9HB07O8ci+vRBdvdGnfP4gBuM8vw7X/G3wDmFhFZEdxzjMAAAAldEVYdGRhdGU6Y3JlYXRlADIwMTgtMDEtMjZUMDc6NTY6MjUrMDE6MDA67pVWAAAAJXRFWHRkYXRlOm1vZGlmeQAyMDE4LTAxLTI2VDA3OjU2OjI1KzAxOjAwS7Mt6gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAAWdEVYdFRpdGxlAGp1ZWppbl9sb2dvIGNvcHlxapmKAAAAV3pUWHRSYXcgcHJvZmlsZSB0eXBlIGlwdGMAAHic4/IMCHFWKCjKT8vMSeVSAAMjCy5jCxMjE0uTFAMTIESANMNkAyOzVCDL2NTIxMzEHMQHy4BIoEouAOoXEXTyQjWVAAAAAElFTkSuQmCC)}.markdown-body h2{position:relative;font-size:20px;border-left:4px solid;padding:0 0 0 10px;margin:30px 0}.markdown-body h3{font-size:16px}.markdown-body ul{list-style:disc outside;margin-left:2em;margin-top:1em}.markdown-body li{line-height:2;color:#595959}.markdown-body img.loaded{margin:0 auto;display:block}.markdown-body blockquote{background:#fff9f9;margin:2em 0;padding:2px 20px;border-left:4px solid #b2aec5}.markdown-body blockquote p{color:#666;line-height:2}.markdown-body a{color:#036aca;border-bottom:1px solid rgba(3,106,202,.8);font-weight:400;text-decoration:none}.markdown-body em strong,.markdown-body strong{color:#036aca}.markdown-body hr{border-top:1px solid #135ce0}.markdown-body pre{overflow:auto}.markdown-body code,.markdown-body pre{overflow:auto;position:relative;line-height:1.75;font-family:Menlo,Monaco,Consolas,Courier New,monospace}.markdown-body pre>code{font-size:12px;padding:15px 12px;margin:0;word-break:normal;display:block;overflow-x:auto;color:#333;background:#f8f8f8}.markdown-body code{word-break:break-word;border-radius:2px;overflow-x:auto;background-color:#fff5f5;color:#ff502c;font-size:.87em;padding:.065em .4em}.markdown-body table{border-collapse:collapse;margin:1rem 0;overflow-x:auto}.markdown-body table td,.markdown-body table th{border:1px solid #dfe2e5;padding:.6em 1em}.markdown-body table tr{border-top:1px solid #dfe2e5}.markdown-body table tr:nth-child(2n){background-color:#f6f8fa}.hljs-comment,.hljs-quote{color:#d4d0ab}.hljs-deletion,.hljs-name,.hljs-regexp,.hljs-selector-class,.hljs-selector-id,.hljs-tag,.hljs-template-variable,.hljs-variable{color:#ffa07a}.hljs-built_in,.hljs-builtin-name,.hljs-link,.hljs-literal,.hljs-meta,.hljs-number,.hljs-params,.hljs-type{color:#f5ab35}.hljs-attribute{color:gold}.hljs-addition,.hljs-bullet,.hljs-string,.hljs-symbol{color:#abe338}.hljs-section,.hljs-title{color:#00e0e0}.hljs-keyword,.hljs-selector-tag{color:#dcc6e0}.markdown-body pre,.markdown-body pre>code.hljs{background:#2b2b2b;color:#f8f8f2}.hljs-emphasis{font-style:italic}.hljs-strong{font-weight:700}@media screen and (-ms-high-contrast:active){.hljs-addition,.hljs-attribute,.hljs-built_in,.hljs-builtin-name,.hljs-bullet,.hljs-comment,.hljs-link,.hljs-literal,.hljs-meta,.hljs-number,.hljs-params,.hljs-quote,.hljs-string,.hljs-symbol,.hljs-type{color:highlight}.hljs-keyword,.hljs-selector-tag{font-weight:700}}
## 前言

IDEA作为一款强大的Java集成开发环境，以其便捷的使用体验、丰富的插件生态和美观的界面设计深受开发者喜爱。

然而，IDEA也存在一些明显的缺点，尤其是在资源占用方面。IDEA的内存占用较大，启动速度较慢，尤其是在同时打开多个项目时，内存较小的电脑可能会不堪重负。

尽管IDEA的内存占用较大，但其带来的编码速度和便捷性是不可忽视的。

本文旨在为那些有兴趣使用Cursor进行Java开发、喜欢自定义插件或配置有限的开发者提供一些建议。

以上是部分原因，最最重要让我使用Cursor的原因是他的代码提示及生成能力

还有阅读分析代码的能力（这让我可以尽情提问别的同事写的代码是什么意思 哈哈）

以及如果你同时用它进行着前端开发的话，那么你后端写的Java bean也将会被Cursor联想应用到前端

等等....

## 目录

- 插件及使用设置

编程环境插件
setting配置
字体颜色、界面颜色、快捷键模仿IDEA
阿里巴巴编码规约插件
常规设置
输出信息输出到调试控制台，而非终端
- 编程环境插件
- setting配置
- 字体颜色、界面颜色、快捷键模仿IDEA
- 阿里巴巴编码规约插件
- 常规设置
- 输出信息输出到调试控制台，而非终端
- 遇到的问题

Java文件名修改后类名未同步
Junit单元测试依赖问题
Organize import后报错
Debug模式中断点卡顿
POM文件报错
this.extensionApi.serverReady is not a function 错误
编写代码时CPU占用过高
- Java文件名修改后类名未同步
- Junit单元测试依赖问题
- Organize import后报错
- Debug模式中断点卡顿
- POM文件报错
- this.extensionApi.serverReady is not a function 错误
- 编写代码时CPU占用过高
- 缺点

依赖搜索功能缺失
复制代码时引用未同步
报错提示不明显
Maven依赖包中的class文件断点无法生效
- 依赖搜索功能缺失
- 复制代码时引用未同步
- 报错提示不明显
- Maven依赖包中的class文件断点无法生效
- 使用指南

@Override 的使用
热部署功能
搜索请求地址对应的URL方法
项目设置及重新构建项目
创建新项目
将输出日志改为调试控制台
- @Override 的使用
- 热部署功能
- 搜索请求地址对应的URL方法
- 项目设置及重新构建项目
- 创建新项目
- 将输出日志改为调试控制台

## 一、插件及使用设置

### 1. 编程环境插件

#### 中文插件

Cursor支持中文语言包，安装后可以将界面语言切换为中文，方便不熟悉英文的开发者使用。

#### Java开发插件包

Cursor提供了多个Java开发相关的插件包，包含以下6个常用插件：

- Language Support for Java：提供Java语言支持。
- Debugger for Java：Java调试工具。
- Test Runner for Java：用于运行JUnit测试。
- Maven for Java：Maven项目管理工具。
- Extension Pack for Java：包管理工具。
- Project Manager for Java：Java项目管理工具。

注意：如果系统只安装了Java 1.8，每次打开Cursor时可能会弹出提示要求选择Java版本。可以通过以下两种方式解决：

- 在settings.json中添加以下配置：
"java.configuration.runtimes": [
 {
 "name": "JavaSE-1.8",
 "path": "E:\Java1.8",//这里是你本地jdk根目录
 "default": true
 }
]

#### Spring Boot相关插件

- Spring Boot Dashboard：在多模块项目中展示可启动的模块，并提供启动和调试按钮。
- Spring Boot Tools：在特定位置自动激活运行。
- Spring Initializr Java Support：用于构建Spring项目，并管理依赖。

效果：

#### Maven插件

Maven插件提供了类似于IDEA中的Maven管理功能，支持刷新Maven项目、使用插件等操作。

### setting配置

文件(左上角按钮)->首选项->设置

```
 "java.errors.incompleteClasspath.severity": "ignore",
 "workbench.colorTheme": "Visual Studio Dark",
 "java.home":"E:/jdk/amazon1.8",
 "java.configuration.maven.userSettings": "E:/apache-maven-3.6.3/conf/settings.xml",
 "maven.executable.path": "E:/apache-maven-3.6.3/bin/mvn.cmd",
 "maven.terminal.useJavaHome": true,
 "maven.terminal.customEnv": [
 {
 "environmentVariable": "JAVA_HOME",
 "value": "E:/jdk/amazon1.8"
 }
 ],
 "extensions.autoUpdate": false,
 "java.configuration.detectJdksAtStart": false,
 "java.configuration.runtimes": [
 {
 "name":"JavaSE-8",
 "path": "E:/jdk/amazon1.8"
 }
 ],
 "java.requirements.JDK11Warning": false

```

这些是关于maven和jdk及一些优化的配置，复制黏贴后结合自己实际的修改就行

### 2. 字体颜色、界面颜色、快捷键模仿IDEA

#### 界面颜色

Cursor支持多种主题，也有类似IDEA的Darcula主题，以保护眼睛并减少视觉疲劳。

#### 字体颜色

通过修改settings.json文件中的editor.tokenColorCustomizations配置，可以自定义字体颜色。

```
"editor.tokenColorCustomizations": {
 "comments": "#619549" // 修改注释颜色
}

```

#### 快捷键

Cursor支持自定义快捷键，可以通过安装插件或手动配置来模仿IDEA的快捷键。

### 3. 阿里巴巴编码规约插件

该插件可以帮助开发者遵循阿里巴巴的Java编码规范，安装后即可使用，支持自定义配置。

### 6. 常规设置

- 自动保存：通过设置Auto Save选项，可以自动保存编辑内容。

- 输出信息到调试控制台：将输出信息输出到调试控制台，而非终端，以便于调试和清空输出。

```
"console": "internalConsole"

```

效果：

## 二、遇到的问题

### 1. Java文件名修改后类名未同步

解决方法：关闭Cursor并重新打开，或手动输入类名。

### 2. Junit单元测试依赖问题

解决方法：确保pom.xml文件中已正确添加JUnit依赖。

### 3. Organize import后报错

解决方法：关闭Cursor并重新打开。

### 4. Debug模式中断点卡顿

解决方法：双击Cursor窗口顶部，切换全屏/非全屏模式。

### 5. POM文件报错

解决方法：检查Maven的settings.xml文件，确保权限配置正确。

### 6. this.extensionApi.serverReady is not a function 错误

解决方法：检查插件版本，确保依赖插件版本兼容。

### 7. 编写代码时CPU占用过高

解决方法：检查插件冲突，结束相关进程。

## 三、缺点

### 1. 依赖搜索功能缺失

Cursor无法像IDEA那样通过快捷键搜索依赖包中的类，只能通过手动跳转。

### 2. 复制代码时引用未同步

解决方法：手动删除并重新输入类名，触发代码提示。

### 3. 报错提示不明显

Cursor的报错提示较为隐晦，开发者需要自行排查问题。

### 4. Maven依赖包中的class文件断点无法生效

目前Cursor暂不支持在Maven依赖包的class文件中设置断点。

## 四、使用指南

### 1. @Override 的使用

通过代码提示 或 右键菜单中的“源代码操作”选项，可以快速生成重写方法。

### 2. 热部署功能

Cursor支持热部署，更新代码后无需重启项目，点击热部署按钮即可快速验证功能。

点一下它就行，非常的好用，没IDEA的热部署那么麻烦

### 3. 搜索请求地址对应的URL方法

通过Spring Boot Dashboard插件，可以快速搜索并定位URL对应的方法。

### 4.打开JAVA项目设置、清理工作空间缓存

在Cursor底部任务栏点击Java:Ready，即可在弹出的菜单栏中选择（如果要重新构建工作空间，Clean Workspace Cache很有用）

### 5.创建新项目

按下ctrl+shift+p后输入create 选择Spring Initializr:Create a Maven Project... 即可创建一个新的基于springboot的maven项目，创建的过程中和IDEA一样 选择需要引入的包、springboot版本、JDK版本等

### 6.将输出日志改为调试控制台

```
"console": "internalConsole"

```

1.在调试面板中点击创建好launch.json文件 2.在该文件的配置启动类的那一个json体中添加"console": "internalConsole" 3.重新启动项目即可（按ctrl+shift+alt+Y可以看控制台日志）

用控制台查看日志的好处是中文不会乱码，关闭控制台不会像关闭终端那样使项目进程结束。

### 7.其他说明

至于调试或者其他那些都是和IDEA操作类似的，自己琢磨下就会了

通过以上优化和配置，Cursor可以成为一个强大的Java开发工具，尤其适合喜欢自定义和折腾的开发者。

尽管在某些方面仍不如IDEA强大，但随着插件的不断丰富，Cursor的潜力不容小觑。

---

*本文转发自原作者，如有侵权请联系删除。*
# 面试官：如何解决按钮重复点击？这个问题挂了80%的人！

> 📎 **原文链接**: [https://juejin.cn/post/7494944356534714406](https://juejin.cn/post/7494944356534714406)
> ⏰ **转发时间**: 2025-06-16 23:12
> 🌟 **内容优化**: 已优化排版格式，提升阅读体验

---

#### 📝 前言还记得上周我们团队在招聘前端工程师，一个看起来经验丰富的候选人坐在我对面。"你们项目中是如何处理按钮重复点击的问题的？"我抛出了这个看似简单的问题。"这个简单，使用防抖就可以了。"他很快回答。然而，当我继续追问细节时，他却陷入了沉思...实际上，这个问题看似简单，但是要真正的解决好，需要考虑很多细节。在我面试了很多候选人中，能完整答出来的不到20%。## ❓ 问题背景在日常开发中，我们经常会遇到这样的场景：• 用户疯狂点击提交按钮
• 表单重复提交导致数据异常
• 批量操作按钮被连续触发这些问题如果处理不当，轻则影响用户体验，重则可能造成数据错误。今天，就让我们通过一个真实的面试场景，逐步深入这个问题## 面试场景面试官：项目中如何处理按钮重复点击的问题？候选人：可以使用防抖（debounce）。💻 **JavaScript 代码示例：**```js
const debouncedSubmit = debounce(submit, 300);
```面试官：那假设我防抖设置了1秒,我现在请求了,但是接口响应比较慢,要3秒,用户在这3秒内点击了多次,那怎么办? 防抖是不是就没用了?> 💡 一般说到这里,很多人就不知道怎么搞了候选人：可以给按钮加上 loading 状态，点击后设置 loading 为 true，等操作完成后再设置为 false。💻 **JavaScript 代码示例：**```js
const [loading, setLoading] = useState(false);const handleSubmit = async () => {
setLoading(true);
try {
await submitData();
} finally {
setLoading(false);
}
}
```面试官：这个思路不错，但是如果项目中有很多按钮都需要这样处理，你会怎么做？候选人：额...每个按钮都写一遍 loading 状态管理？面试官：那样就会有很多重复代码，有没有想过怎么封装呢？> 💡 到这里也卡掉了很多人## ✅ 解决方案我们可以封装一个自定义 Hook💻 **JavaScript 代码示例：**```js
import {useState,useCallback,useRef} from 'react'function useLock(asyncFn) {
const [loading, setLoading] = useState(false)
const asyncFnRef = useRef(null)
asyncFnRef.current = asyncFn
const run = useCallback(async (...args) => {
if(loading) return
setLoading(true)
try {
await asyncFnRef.current(...args)
} finally {
setLoading(false)
}
}, [loading])return [loading,run]
}
```然后封装一个通用的 Button 组件💻 **JavaScript 代码示例：**```js
import {Button as AntButton} from 'antd'const Button = ({onClick,...props})=>{
const {loading, run} = useLock(onClick || (()=> {}))
return <AntButton loading={loading} {...props} onClick={run}></button>
}
```## 🚀 使用示例💻 **JavaScript 代码示例：**```js
const Demo = () => {
const handleSubmit = async () => {
await new Promise(resolve => setTimeout(resolve, 2000))
console.log('提交成功')
}return (
<Button onClick={handleSubmit}>
提交
</Button>
)
}
```可以看到 在 handleSubmit 执行的时候 Button 会自动添加 loading, 在请求完成后 loading 会自动变为 false。## 方案优势• 零侵入性 ：使用方式与普通按钮完全一致
• 自动处理 ：自动管理 loading 状态，无需手动控制希望这篇文章对你有帮助！如果觉得有用，别忘了点个赞 👍## 讨论你在项目中是如何处理按钮重复点击的问题的？欢迎在评论区分享你的解决方案！

---

### 📝 转发说明

- 🔗 **原文链接**: 请点击上方链接查看完整原文
- 📱 **格式优化**: 已针对移动端阅读体验进行优化
- ⚖️ **版权声明**: 本文转发自原作者，如有侵权请联系删除

*感谢原作者的精彩分享！* 🙏
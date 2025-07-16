import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * 路由跳转时自动滚动到页面顶部的组件
 */
const ScrollToTop: React.FC = () => {
  const { pathname } = useLocation()

  useEffect(() => {
    // 强制滚动到页面顶部，使用多种方法确保成功
    const scrollToTop = () => {
      // 方法1: 使用window.scrollTo
      window.scrollTo({
        top: 0,
        left: 0,
        behavior: 'instant'
      })
      
      // 方法2: 直接设置scrollTop
      document.documentElement.scrollTop = 0
      document.body.scrollTop = 0
      
      // 方法3: 针对可能的滚动容器
      const mainContent = document.querySelector('.main-content')
      if (mainContent) {
        mainContent.scrollTop = 0
      }
      
      const pageContainer = document.querySelector('.page-container')
      if (pageContainer) {
        pageContainer.scrollTop = 0
      }
    }

    // 立即执行
    scrollToTop()
    
    // 延迟执行，确保在组件渲染完成后也能滚动到顶部
    const timeoutId = setTimeout(scrollToTop, 0)
    
    return () => clearTimeout(timeoutId)
  }, [pathname])

  return null
}

export default ScrollToTop 
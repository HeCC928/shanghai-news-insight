import type { Metadata } from 'next';
import { Providers } from '@/components/providers';
import './globals.css';
export const metadata:Metadata={title:'沪讯 · 公司资讯与估值研究助手',description:'连接公司新闻、财务证据与可解释估值。'};
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="zh-CN"><body><Providers>{children}</Providers></body></html>; }

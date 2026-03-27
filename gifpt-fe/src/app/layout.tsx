// next-intl 미들웨어가 /로 오는 요청을 [locale]로 리다이렉트함
// 이 layout은 [locale]/layout.tsx가 대신함
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}

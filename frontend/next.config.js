/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  i18n: {
    locales: ['en', 'de', 'fr', 'es', 'it', 'nl', 'pl', 'pt'],
    defaultLocale: 'en',
  },
}

module.exports = nextConfig

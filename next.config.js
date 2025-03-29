/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_TINYMCE_KEY: process.env.TINYMCE_KEY,
  },
}

module.exports = nextConfig 
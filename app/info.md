# app/info.md

> **파일명**: app/info.md  
> **최종 수정일**: 2026-04-07  
> **문서 해시**: SHA256:7dca10ef4f11f9e64a840c8d576f882944de7b3ccd431c2bf4cfd8b01314eb6a  
> **문서 역할**: 프론트(scaffold) 스택·구성 요약  
> **문서 우선순위**: 96  
> **연관 문서**: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, ../README.md, DIRECTORY_SPEC.md  
> **참조 규칙**: Vite·Tailwind·컴포넌트 구조 변경 시 본 문서를 갱신한다.

---

Using Node.js 20, Tailwind CSS v3.4.19, and Vite v7.2.4

Tailwind CSS has been set up with the shadcn theme

Setup complete: /mnt/okcomputer/output/app

Components (40+):
  accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb,
  button-group, button, calendar, card, carousel, chart, checkbox, collapsible,
  command, context-menu, dialog, drawer, dropdown-menu, empty, field, form,
  hover-card, input-group, input-otp, input, item, kbd, label, menubar,
  navigation-menu, pagination, popover, progress, radio-group, resizable,
  scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner,
  spinner, switch, table, tabs, textarea, toggle-group, toggle, tooltip

Usage:
  import { Button } from '@/components/ui/button'
  import { Card, CardHeader, CardTitle } from '@/components/ui/card'

Structure:
  src/sections/        Page sections
  src/hooks/           Custom hooks
  src/types/           Type definitions
  src/App.css          Styles specific to the Webapp
  src/App.tsx          Root React component
  src/index.css        Global styles
  src/main.tsx         Entry point for rendering the Webapp
  index.html           Entry point for the Webapp
  tailwind.config.js   Configures Tailwind's theme, plugins, etc.
  vite.config.ts       Main build and dev server settings for Vite
  postcss.config.js    Config file for CSS post-processing tools
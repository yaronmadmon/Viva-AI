This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

## Viewing your project and the teaching avatar

1. **Run the backend** (from repo root) so the frontend can load projects and artifacts:
   ```bash
   # PowerShell example; use SQLite for quick local run
   $env:DATABASE_URL="sqlite+aiosqlite:///ramp_dev.db"; $env:DEBUG="true"; $env:SECRET_KEY="your-secret-key-min-32-chars"; python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
   ```
2. **Run the frontend**: from `frontend/`, run `npm run dev` and open http://localhost:3000.
3. **Log in** (or register). If you use the same SQLite DB as the script, you can log in as `e2e-test@example.com` / `TestPassword123`.
4. **Student dashboard**: go to **Student** (or Dashboard). Your projects appear as cards; click one to open the project workspace.
5. **Teaching avatar**: the guide avatar appears in the **left sidebar** when you’re on the student (or admin) dashboard. Click the avatar to cycle through short tips. It’s there to teach and guide you through research steps, artifacts, and mastery.

Projects created via the API have a title and description but **no artifacts yet**. Use “New artifact” in the project to add content; Guidance, Curriculum, and Mastery pages then become meaningful as you add and link artifacts.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { boundedBody, createSession, sameOrigin } from "@/lib/server-auth";

let attempts: number[] = [];
export async function POST(request: NextRequest) {
  if (!sameOrigin(request))
    return NextResponse.json(
      { message: "Same-origin request required" },
      { status: 403 },
    );
  const now = Date.now();
  attempts = attempts.filter((time) => now - time < 60000);
  if (attempts.length >= 10)
    return NextResponse.json(
      { message: "Too many attempts. Try again in a minute." },
      { status: 429 },
    );
  attempts.push(now);
  let input: { key?: unknown };
  try {
    input = JSON.parse(await boundedBody(request, 4096));
    if (!input || typeof input !== "object") throw new Error("Invalid input");
  } catch {
    return NextResponse.json({ message: "Invalid request" }, { status: 400 });
  }
  const configured = process.env.FENER_ADMIN_KEY ?? "";
  if (
    typeof input.key !== "string" ||
    !configured ||
    Buffer.byteLength(input.key) !== Buffer.byteLength(configured) ||
    !timingSafeEqual(Buffer.from(input.key), Buffer.from(configured))
  )
    return NextResponse.json(
      { message: "Invalid administration key" },
      { status: 401 },
    );
  const response = NextResponse.json({ authenticated: true });
  response.cookies.set("fener-session", createSession(configured), {
    httpOnly: true,
    sameSite: "strict",
    secure: request.headers.get("origin")?.startsWith("https://") ?? false,
    path: "/",
    maxAge: 28800,
  });
  return response;
}
export async function DELETE(request: NextRequest) {
  if (!sameOrigin(request))
    return NextResponse.json(
      { message: "Same-origin request required" },
      { status: 403 },
    );
  const response = NextResponse.json({ authenticated: false });
  response.cookies.delete("fener-session");
  return response;
}

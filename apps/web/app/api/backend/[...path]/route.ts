import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { boundedBody, sameOrigin, validSession } from "@/lib/server-auth";

const allowed = new Set([
  "models",
  "providers",
  "deployments",
  "benchmarks",
  "market-events",
  "observations",
  "sources",
  "overview",
  "recommendations",
  "data-health",
  "research",
  "internal",
  "analytics",
]);
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (
    !allowed.has(path[0]) ||
    path.some(
      (part) => part === ".." || part.includes("/") || part.includes("\\"),
    )
  )
    return NextResponse.json(
      { message: "Unknown API resource" },
      { status: 404 },
    );
  if (request.method !== "GET" && !sameOrigin(request))
    return NextResponse.json(
      { message: "Same-origin request required" },
      { status: 403 },
    );
  const key = process.env.FENER_ADMIN_KEY ?? "";
  const cookie = (await cookies()).get("fener-session")?.value ?? "";
  const authenticated = validSession(cookie, key);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (authenticated) headers.Authorization = `Bearer ${key}`;
  let body: string | undefined;
  try {
    body =
      request.method === "GET" ? undefined : await boundedBody(request, 131072);
  } catch {
    return NextResponse.json({ message: "Request too large" }, { status: 413 });
  }
  try {
    const response = await fetch(
      `${process.env.FENER_API_URL ?? "http://127.0.0.1:8000"}/api/v1/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(60000),
        redirect: "error",
      },
    );
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        message:
          "Fener API is unavailable. Start the API service and check database migrations.",
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;

import { Link, ScrollRestoration, createRootRoute, useLocation } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/router-devtools";
import { Body, Head, Html, Meta, Scripts, Title } from "@tanstack/start";

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  const location = useLocation();

  return (
    <Html lang="en">
      <Head>
        <Title>Code Documentation Assistant</Title>
        <Meta charSet="utf-8" />
        <Meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <Body>
        <div className="min-h-screen bg-background">
          <nav className="border-b">
            <div className="container mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <Link to="/" className="text-xl font-bold">
                  Code Doc Assistant
                </Link>
                <div className="flex gap-4">
                  <Link to="/" className="text-sm hover:underline">
                    Home
                  </Link>
                  <Link to="/upload" className="text-sm hover:underline">
                    Upload
                  </Link>
                </div>
              </div>
            </div>
          </nav>
          <ScrollRestoration />
          <div className="children" />
        </div>
        <Scripts />
        <TanStackRouterDevtools position="bottom-right" />
      </Body>
    </Html>
  );
}

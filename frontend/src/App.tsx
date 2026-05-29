import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import LandingPage from "./pages/LandingPage";
import BlockchainExplorer from "./pages/BlockchainExplorer";
import WhatsAppPage from "./pages/WhatsAppPage";
import BlockchainVerificationPortal from "./pages/BlockchainVerificationPortal";
import NotFound from "./pages/NotFound";
import { DemoChecklist } from "./components/DemoChecklist";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/whatsapp" element={<WhatsAppPage />} />
          <Route path="/blockchain/explorer" element={<BlockchainExplorer />} />
          <Route path="/blockchain/verify" element={<BlockchainVerificationPortal />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
      {/* Demo checklist — visible only when ?demo=true in URL */}
      <DemoChecklist />
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
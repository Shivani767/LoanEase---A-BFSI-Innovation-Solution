import { useEffect, useRef, useState } from "react";
import { Hero } from "@/components/Hero";
import { ChatInterface } from "@/components/ChatInterface";

const Index = () => {
  const [showChat, setShowChat] = useState(false);
  const chatAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showChat) return;

    requestAnimationFrame(() => {
      chatAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [showChat]);

  return (
    <>
      <Hero onStartChat={() => setShowChat(true)} />
      <div ref={chatAnchorRef}>{showChat && <ChatInterface onClose={() => setShowChat(false)} />}</div>
    </>
  );
};

export default Index;

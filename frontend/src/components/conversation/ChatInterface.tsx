"use client";

import * as React from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Message, Conversation } from "@/types/api";

interface ChatInterfaceProps {
  conversationId?: string;
  onConversationStart?: (conversation: Conversation) => void;
  onMessageSend?: (message: string) => Promise<void>;
  className?: string;
}

interface ChatMessage extends Message {
  isLoading?: boolean;
}

export function ChatInterface({
  conversationId,
  onConversationStart,
  onMessageSend,
  className,
}: ChatInterfaceProps) {
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [input, setInput] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Initialize conversation on mount
  React.useEffect(() => {
    if (!conversationId && onConversationStart) {
      initializeConversation();
    }
  }, []);

  const initializeConversation = async () => {
    try {
      const response = await fetch("/api/v1/conversations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          language: navigator.language.split("-")[0] || "en",
        }),
      });

      if (!response.ok) throw new Error("Failed to start conversation");

      const conversation: Conversation = await response.json();
      onConversationStart?.(conversation);

      // Add initial greeting message
      setMessages([
        {
          id: "initial",
          conversationId: conversation.id,
          role: "assistant",
          content:
            "Guten Tag! Ich bin Ihr AI Offer Agent. Ich helfe Ihnen dabei, ein maßgeschneidertes Angebot für Ihr IT-Projekt zu erstellen. Erzählen Sie mir zunächst etwas über Ihr Projekt.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error("Failed to initialize conversation:", error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      conversationId: conversationId || "",
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      if (onMessageSend) {
        await onMessageSend(userMessage.content);
      } else {
        // Default API call
        const response = await fetch(
          `/api/v1/conversations/${conversationId}/messages`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              message: userMessage.content,
            }),
          }
        );

        if (!response.ok) throw new Error("Failed to send message");

        const data = await response.json();

        // Add assistant response
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          conversationId: conversationId || "",
          role: "assistant",
          content: data.response || data.message,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          conversationId: conversationId || "",
          role: "assistant",
          content:
            "Entschuldigung, es gab einen Fehler bei der Verarbeitung Ihrer Nachricht. Bitte versuchen Sie es erneut.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className={cn("flex flex-col h-[600px]", className)}>
      <CardHeader>
        <CardTitle>AI Offer Agent</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-0">
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex",
                message.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-4 py-2",
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <span className="text-xs opacity-70 mt-1 block">
                  {new Date(message.timestamp).toLocaleTimeString("de-DE", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-4 py-2">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form
          onSubmit={handleSendMessage}
          className="border-t p-4 flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ihre Nachricht..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

import { Button } from "@/components/ui/button";
import { MessageCircle, Shield, Zap, Clock, CheckCircle, Check, X, Minus } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ChannelSelector } from "./ChannelSelector";

interface HeroProps {
  onStartChat: () => void;
}

export const Hero = ({ onStartChat }: HeroProps) => {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 bg-card/80 backdrop-blur-md border-b border-border z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">₹</span>
            </div>
            <span className="font-display font-bold text-xl text-foreground">LoanEase</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="text-sm text-muted-foreground hover:text-foreground transition-colors">How It Works</a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="container mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8 animate-slide-up">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-accent/10 rounded-full border border-accent/20">
                <Zap className="w-4 h-4 text-accent" />
                <span className="text-sm font-medium text-accent">Instant Loan Approval</span>
              </div>
              
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-display font-bold text-foreground leading-tight">
                Get Personal Loans
                <span className="text-gradient block">In Minutes</span>
              </h1>
              
              <p className="text-lg text-muted-foreground max-w-xl">
                Experience seamless loan applications with our AI-powered assistant. 
                From KYC to sanction letter – all in one conversation.
              </p>

              <ChannelSelector onWebChat={onStartChat} />

              <div className="flex items-center gap-6 pt-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-success" />
                  <span className="text-sm text-muted-foreground">No paperwork</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-success" />
                  <span className="text-sm text-muted-foreground">100% digital</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-success" />
                  <span className="text-sm text-muted-foreground">Secure</span>
                </div>
              </div>
            </div>

            <div className="relative animate-float hidden lg:block">
              <div className="absolute inset-0 bg-gradient-to-r from-accent/20 to-primary/20 rounded-3xl blur-3xl" />
              <div className="relative bg-card rounded-3xl p-8 border border-border shadow-2xl">
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center">
                      <MessageCircle className="w-6 h-6 text-primary-foreground" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground">Loan Assistant</h3>
                      <p className="text-sm text-accent">Online • Ready to help</p>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="bg-secondary rounded-2xl rounded-tl-md p-4 max-w-[80%]">
                      <p className="text-sm text-foreground">Hello! I'll help you find the perfect loan. What amount are you looking for?</p>
                    </div>
                    <div className="bg-primary rounded-2xl rounded-tr-md p-4 max-w-[80%] ml-auto">
                      <p className="text-sm text-primary-foreground">I need ₹5,00,000 for home renovation</p>
                    </div>
                    <div className="bg-secondary rounded-2xl rounded-tl-md p-4 max-w-[80%]">
                      <p className="text-sm text-foreground">Great! Let me check your eligibility...</p>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <div className="flex-1 h-10 bg-muted rounded-full" />
                    <div className="w-10 h-10 bg-accent rounded-full flex items-center justify-center">
                      <span className="text-accent-foreground">→</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-4 bg-secondary/30">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-foreground mb-4">
              Why Choose LoanEase?
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Our AI-powered platform makes loan applications faster, smarter, and more secure than ever.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-card p-8 rounded-2xl border border-border hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="w-14 h-14 rounded-xl bg-accent/10 flex items-center justify-center mb-6">
                <Clock className="w-7 h-7 text-accent" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-3">5-Minute Approval</h3>
              <p className="text-muted-foreground">
                Get instant decisions with our AI underwriting system. No waiting, no delays.
              </p>
            </div>

            <div className="bg-card p-8 rounded-2xl border border-border hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="w-14 h-14 rounded-xl bg-accent/10 flex items-center justify-center mb-6">
                <Shield className="w-7 h-7 text-accent" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-3">Blockchain Security</h3>
              <p className="text-muted-foreground">
                Your sanction letter is secured on blockchain for tamper-proof verification.
              </p>
            </div>

            <div className="bg-card p-8 rounded-2xl border border-border hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="w-14 h-14 rounded-xl bg-accent/10 flex items-center justify-center mb-6">
                <Zap className="w-7 h-7 text-accent" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-3">Smart Negotiation</h3>
              <p className="text-muted-foreground">
                Customize your loan terms with real-time EMI calculations and rate adjustments.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Comparison Section */}
      <section className="py-24 px-4 bg-background">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-foreground mb-4">
              LoanEase vs Traditional Lending
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              See why borrowers choose LoanEase over banks and traditional loan agents.
            </p>
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Card 1: Bar Chart */}
            <div className="bg-card p-8 rounded-2xl border border-border flex flex-col h-full">
              <h3 className="text-xl font-semibold text-foreground mb-6">Average Loan Approval Time</h3>
              <div className="flex-1 min-h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: 'Bank Branch', time: 10, label: '7-10 days' },
                      { name: 'Bank App', time: 3, label: '2-3 days' },
                      { name: 'Loan Agent', time: 5, label: '3-5 days' },
                      { name: 'LoanEase (AI)', time: 0.1, label: '< 5 mins' },
                    ]}
                    layout="vertical"
                    margin={{ left: 20, right: 40, top: 0, bottom: 0 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis 
                      dataKey="name" 
                      type="category" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#94a3b8', fontSize: 12 }}
                      width={100}
                    />
                    <Tooltip
                      cursor={{ fill: 'transparent' }}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="bg-popover border border-border px-3 py-2 rounded-lg shadow-xl">
                              <p className="text-sm font-medium text-foreground">{payload[0].payload.label}</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar dataKey="time" radius={[0, 4, 4, 0]} barSize={24}>
                      {[0, 1, 2, 3].map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 3 ? '#F5C518' : '#4B5563'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Card 2: Feature Matrix */}
            <div className="bg-card p-8 rounded-2xl border border-border lg:col-span-1 overflow-x-auto">
              <h3 className="text-xl font-semibold text-foreground mb-6">Feature Matrix</h3>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="pb-4 font-medium text-muted-foreground">Feature</th>
                    <th className="pb-4 font-medium text-muted-foreground text-center">Bank</th>
                    <th className="pb-4 font-medium text-muted-foreground text-center">Agent</th>
                    <th className="pb-4 font-medium text-muted-foreground text-center text-accent">LoanEase</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {[
                    { name: 'Personalized Offers', bank: 'partial', agent: 'no', loanease: 'yes' },
                    { name: 'Real-Time Negotiation', bank: 'no', agent: 'partial', loanease: 'yes' },
                    { name: '24/7 Availability', bank: 'no', agent: 'no', loanease: 'yes' },
                    { name: 'Instant Sanction', bank: 'no', agent: 'no', loanease: 'yes' },
                    { name: 'Blockchain Audit', bank: 'no', agent: 'no', loanease: 'yes' },
                    { name: 'WhatsApp Access', bank: 'no', agent: 'yes', loanease: 'yes' },
                    { name: 'Zero Paperwork', bank: 'no', agent: 'no', loanease: 'yes' },
                  ].map((row, i) => (
                    <tr key={i}>
                      <td className="py-3 text-foreground/80">{row.name}</td>
                      <td className="py-3 text-center">
                        {row.bank === 'yes' ? <Check className="w-4 h-4 text-accent mx-auto" /> : row.bank === 'partial' ? <Minus className="w-4 h-4 text-muted-foreground mx-auto" /> : <X className="w-4 h-4 text-muted-foreground/30 mx-auto" />}
                      </td>
                      <td className="py-3 text-center">
                        {row.agent === 'yes' ? <Check className="w-4 h-4 text-accent mx-auto" /> : row.agent === 'partial' ? <Minus className="w-4 h-4 text-muted-foreground mx-auto" /> : <X className="w-4 h-4 text-muted-foreground/30 mx-auto" />}
                      </td>
                      <td className="py-3 text-center font-bold">
                        <Check className="w-5 h-5 text-accent mx-auto" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Card 3: Impact Numbers */}
            <div className="space-y-4 flex flex-col justify-between">
              <div className="bg-card p-8 rounded-2xl border border-border hover:shadow-lg transition-all duration-300">
                <div className="text-4xl font-bold text-accent mb-2">75% faster</div>
                <div className="text-foreground font-semibold mb-1">vs traditional bank</div>
                <p className="text-sm text-muted-foreground">Loan decisions in minutes, not weeks.</p>
              </div>
              <div className="bg-card p-8 rounded-2xl border border-border hover:shadow-lg transition-all duration-300">
                <div className="text-4xl font-bold text-accent mb-2">50% reduction</div>
                <div className="text-foreground font-semibold mb-1">in manual effort</div>
                <p className="text-sm text-muted-foreground">Automated agent workflows for efficiency.</p>
              </div>
              <div className="bg-card p-8 rounded-2xl border border-border hover:shadow-lg transition-all duration-300">
                <div className="text-4xl font-bold text-accent mb-2">100% digital</div>
                <div className="text-foreground font-semibold mb-1">zero physical touchpoints</div>
                <p className="text-sm text-muted-foreground">From KYC to signed sanction letter online.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-foreground mb-4">
              How LoanEase Works
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Complete your entire loan journey in a single guided conversation with our AI assistant.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-card p-8 rounded-2xl border border-border">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center mb-4">
                <MessageCircle className="w-5 h-5 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">Start the Chat</h3>
              <p className="text-sm text-muted-foreground">
                Share basic details like your name, PAN, and loan needs with our conversational assistant.
              </p>
            </div>

            <div className="bg-card p-8 rounded-2xl border border-border">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center mb-4">
                <Shield className="w-5 h-5 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">Check Eligibility</h3>
              <p className="text-sm text-muted-foreground">
                We instantly assess your credit profile and show you personalized loan offers and EMIs.
              </p>
            </div>

            <div className="bg-card p-8 rounded-2xl border border-border">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center mb-4">
                <Clock className="w-5 h-5 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">Get Sanction Letter</h3>
              <p className="text-sm text-muted-foreground">
                Select a plan you like and instantly receive a digital sanction letter you can share or download.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <div className="bg-gradient-hero rounded-3xl p-12 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg%20width%3D%2260%22%20height%3D%2260%22%20viewBox%3D%220%200%2060%2060%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cg%20fill%3D%22none%22%20fill-rule%3D%22evenodd%22%3E%3Cg%20fill%3D%22%23ffffff%22%20fill-opacity%3D%220.05%22%3E%3Cpath%20d%3D%22M36%2034v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6%2034v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6%204V0H4v4H0v2h4v4h2V6h4V4H6z%22%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E')] opacity-50" />
            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl font-display font-bold text-foreground mb-4">
                Ready to Get Started?
              </h2>
              <p className="text-foreground/80 max-w-2xl mx-auto mb-8">
                Join thousands of satisfied customers who've simplified their loan journey with LoanEase.
              </p>
              <Button 
                variant="accent" 
                size="xl" 
                onClick={onStartChat}
                className="shadow-glow"
              >
                <MessageCircle className="w-5 h-5 mr-2" />
                Start Your Application
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-border">
        <div className="container mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">₹</span>
            </div>
            <span className="font-display font-semibold text-foreground">LoanEase</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © 2025 LoanEase. All rights reserved. A BFSI Solution.
          </p>
        </div>
      </footer>
    </div>
  );
};

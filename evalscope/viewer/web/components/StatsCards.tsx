"use client";

import { BarChart3, TrendingUp, CheckCircle, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatScore } from "@/lib/utils";

interface StatsCardsProps {
  totalRuns: number;
  avgScore: number | null;
  successRate: number | null;
  lastRunTime: string | null;
}

export function StatsCards({
  totalRuns,
  avgScore,
  successRate,
  lastRunTime,
}: StatsCardsProps) {
  const stats = [
    {
      title: "Total Runs",
      value: totalRuns.toString(),
      icon: BarChart3,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
    },
    {
      title: "Avg Score",
      value: avgScore !== null ? formatScore(avgScore) : "N/A",
      icon: TrendingUp,
      color: "text-green-600",
      bgColor: "bg-green-50",
    },
    {
      title: "Success Rate",
      value: successRate !== null ? `${(successRate * 100).toFixed(0)}%` : "N/A",
      icon: CheckCircle,
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
    },
    {
      title: "Last Run",
      value: lastRunTime || "N/A",
      icon: Clock,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {stats.map((stat) => (
        <Card key={stat.title} className="border-0 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-500">{stat.title}</p>
                <p className="text-xl font-semibold text-gray-900">
                  {stat.value}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

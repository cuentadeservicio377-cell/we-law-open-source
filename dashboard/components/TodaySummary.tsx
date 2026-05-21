import { AlertCircle, CheckSquare, FileText, Scale } from "lucide-react";
import StatCard from "@/components/StatCard";

type TodaySummaryProps = {
  activeMatters: number;
  pendingTasks: number;
  draftDocuments: number;
  pendingApprovals: number;
  openIntakes: number;
  templateCount: number;
};

export default function TodaySummary({
  activeMatters,
  pendingTasks,
  draftDocuments,
  pendingApprovals,
  openIntakes,
  templateCount,
}: TodaySummaryProps) {
  return (
    <div className="grid stats">
      <StatCard label="Asuntos en marcha" value={activeMatters} detail="lo que sigue vivo" icon={<Scale size={22} />} />
      <StatCard label="Trabajo por asignar" value={pendingTasks} detail="pendiente de tu decisión" icon={<CheckSquare size={22} />} />
      <StatCard label="Documentos en borrador" value={draftDocuments} detail="todavía en revisión" icon={<FileText size={22} />} />
      <StatCard label="Aprobaciones del abogado" value={pendingApprovals} detail="esperando tu visto bueno" icon={<AlertCircle size={22} />} />
      <StatCard label="Intakes abiertos" value={openIntakes} detail="para cerrar información" icon={<AlertCircle size={22} />} />
      <StatCard label="Plantillas listas" value={templateCount} detail="biblioteca local" icon={<FileText size={22} />} />
    </div>
  );
}

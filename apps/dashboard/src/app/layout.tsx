import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = { title: "ORACLE Intelligence", description: "Prediction-market intelligence and positive expected-value research" };

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><div className="shell"><aside><div className="brand"><span>◉</span> ORACLE</div><nav><a className="active" href="#markets">Intelligence</a><a href="#portfolio">Portfolio</a><a href="#research">Research</a><a href="#calibration">Calibration</a></nav><div className="status"><i /> Systems operational</div></aside><main>{children}</main></div></body></html>;
}

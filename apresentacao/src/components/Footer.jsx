import "./footer.css";

export default function Footer() {
  const year = new Date().getFullYear();
  const email = "contato@poshboard.org";
  return (
    <footer className="app-footer">
      <div className="footer-inner">
        <div className="footer-center">
          © {year} Poshboard — Todos os direitos reservados
        </div>     
      </div>
    </footer>
  );
}

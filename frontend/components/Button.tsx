import { ReactNode } from "react";

interface Props {
  type?: "button" | "submit" | "reset" | undefined,
  children: ReactNode,
  className?: string | undefined,
  replace?: boolean,
  onClick?: (e: any) => void | Promise<any> | any
}

export default function Button(props: Props) {
  const newClass = props.className;
  const baseClass = "font-bold uppercase tracking-widest p-4";
  const otherBaseClass = "border-2 border-white";
  const classNames = !newClass ? `${baseClass} ${otherBaseClass}` : props.replace ? newClass : `${baseClass} ${newClass} ${otherBaseClass}`;
  return (
    <button
      type={props.type || "button"}
      className={classNames}
      onClick={props.onClick}
    >
      {props.children}
    </button>
  )
}
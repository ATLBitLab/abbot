import { ReactNode } from "react";

interface Props {
    children: ReactNode,
    className?: string | undefined,
}

export default function Row(props: Props) {
    const newClass = props.className
    const baseClasses = "flex flex-row items-center justify-between";
    const classNames = !newClass ? baseClasses : `${baseClasses} ${newClass}`
    return (
        <div className={classNames}>
            {props.children}
        </div>
    )
}
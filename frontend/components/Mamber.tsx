import Image from "next/image";

type MemberProps = {
  name: string;
  image: string;
  bio: string;
};

export default function Member({ name, image, bio }: MemberProps) {
  return (
    <div
      className="member"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <div
        style={{
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <Image
          src={image}
          alt={name}
          width={200}
          height={200}
          style={{ borderRadius: "50%" }}
          className="member-image"
        />
        <h3>{name}</h3>
      </div>
      <div dangerouslySetInnerHTML={{ __html: bio }} />
    </div>
  );
}

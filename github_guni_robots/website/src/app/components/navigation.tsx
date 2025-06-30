"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import  { SignInButton , UserButton , SignedIn , SignedOut} from '@clerk/nextjs';
export const Navigation =() => {
    const pathname = usePathname();
    return(
    <nav>
        <Link href="/" className={pathname === "/" ? "font-bold mr-4" : "text-blue-500 mr-4"}>Home</Link>    
        <Link href="/about" className={pathname === "/about" ? "font-bold mr-4" : "text-blue-500 mr-4"}>About</Link>
        <Link href="/user-dashboard" className={pathname === "/remote_control" ? "font-bold mr-4" : "text-blue-500 mr-4" }>Dashboard</Link>
        <SignedOut>
        <SignInButton mode="modal"/>
        </SignedOut>
        <SignedIn>
        <UserButton/>
        </SignedIn>
   </nav>
);
};